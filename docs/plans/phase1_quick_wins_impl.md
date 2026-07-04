---
name: Phase 1 — Quick Wins (implementation)
phase: 1
overview: Feedback widget emailing product owner + fix two known QA bugs (auto-include owner as player, 2.5h inactivity warning).
prerequisites: [phase0]
blocks: [phase2]
estimated_duration: 3-5 days
todos:
  - id: p1-feedback-backend
    content: "Commit 1: feedback model + migration + POST /api/feedback + email"
    status: pending
  - id: p1-feedback-frontend
    content: "Commit 2: FeedbackButton FAB + modal in AppShell"
    status: pending
  - id: p1-bug-owner-player
    content: "Commit 3: Auto-include owner as player (backend + GamePlayersPage UX)"
    status: pending
  - id: p1-bug-inactivity
    content: "Commit 4: last_activity_at + inactivity warning modal on play page"
    status: pending
isProject: false
---

# Phase 1 — Quick Wins: Low-Level Implementation Plan

**Roadmap context:** [Product Roadmap 2026](product_roadmap_2026_36ec752e.plan.md) → Phase 1

**Priorities covered:** #1 Feedback, known QA bugs

**Depends on:** [Phase 0](phase0_foundation_impl.plan.md) (release pipeline recommended before prod deploy)

---

## Acceptance criteria

- [ ] Authenticated user can submit feedback; email arrives at `FEEDBACK_TO_EMAIL`
- [ ] Rate limit: max 5 submissions/user/hour → 429
- [ ] Owner is always a player; player picker shows "You" as fixed, pick opponents only
- [ ] Active game with no turn for 2h 55m shows warning modal; user can Continue or End game
- [ ] Tests cover feedback API and owner-player injection

---

## Commit 1: Feedback backend

### Migration `005_feedback.py`

**New table `feedback_submissions`:**

| Column | Type | Notes |
|--------|------|-------|
| id | int PK | |
| user_id | int FK users | |
| category | varchar(50) nullable | bug, idea, other |
| message | text | max 2000 chars |
| page_url | varchar(512) nullable | |
| game_id | int nullable | |
| created_at | datetime | index with user_id for rate limit |

### Model

**File:** [`backend/app/models.py`](../../dev/scrabble-helper/backend/app/models.py) — add `FeedbackSubmission`

### Config

**File:** [`backend/app/config.py`](../../dev/scrabble-helper/backend/app/config.py):

```python
feedback_to_email: str = ""
feedback_rate_limit_per_hour: int = 5
```

Fly secret: `FEEDBACK_TO_EMAIL=you@example.com`

### Email

**File:** [`backend/app/email_send.py`](../../dev/scrabble-helper/backend/app/email_send.py):

```python
def send_feedback_email(
    *, to_email: str, from_user: User, message: str,
    category: str | None, page_url: str | None, game_id: int | None,
) -> None: ...
```

Subject: `[Scrabble Helper Feedback] {category or 'General'} from {from_user.email}`

### Schema + route

**File:** [`backend/app/schemas.py`](../../dev/scrabble-helper/backend/app/schemas.py):

```python
class FeedbackCreate(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    category: Literal["bug", "idea", "other"] | None = None
    page_url: str | None = Field(default=None, max_length=512)
    game_id: int | None = None
```

**File:** [`backend/app/main.py`](../../dev/scrabble-helper/backend/app/main.py):

```python
@app.post("/api/feedback", status_code=204)
def submit_feedback(body: FeedbackCreate, request: Request, db: Session = Depends(get_db)):
    user = auth.require_user(request, db)
    # rate limit query: count where user_id and created_at > now - 1h
    # insert row, send email (log if SMTP missing, still 204)
```

Return 503 if SMTP not configured and not dev (mirror verification email behavior).

### Tests

**New file:** `backend/tests/test_feedback.py`
- 401 without session
- 204 with valid body
- 429 on 6th submission in hour
- Email mocked via monkeypatch

---

## Commit 2: Feedback frontend

### API

**File:** [`frontend/src/api.ts`](../../dev/scrabble-helper/frontend/src/api.ts):

```typescript
export async function submitFeedback(body: {
  message: string;
  category?: "bug" | "idea" | "other";
  page_url?: string;
  game_id?: number;
}): Promise<void>
```

### Components

**New:** `frontend/src/components/FeedbackButton.tsx`
- Fixed position `bottom: 1rem; right: 1rem; z-index: 100`
- On `/game/:id/play`: use smaller icon-only FAB or `bottom: 5rem` to avoid score buttons
- Modal: textarea, category `<select>`, Submit/Cancel
- Auto-fill: `window.location.pathname`, parse game id from `/game/(\d+)`

**File:** [`frontend/src/App.tsx`](../../dev/scrabble-helper/frontend/src/App.tsx) — mount inside `ProtectedShell` only (not login)

### Styles

**File:** [`frontend/src/styles.css`](../../dev/scrabble-helper/frontend/src/styles.css):

```css
.feedback-fab { ... }
.feedback-modal { ... }
```

---

## Commit 3: Auto-include owner as player

### Problem

[`GamePlayersPage.tsx`](../../dev/scrabble-helper/frontend/src/pages/GamePlayersPage.tsx) requires manual self-selection; [`set_game_players`](../../dev/scrabble-helper/backend/app/services.py) needs ≥2 player IDs.

### Backend

**New function in [`services.py`](../../dev/scrabble-helper/backend/app/services.py):**

```python
def ensure_owner_player(db: Session, user: User) -> Player:
    """Player representing the game owner (linked to their account)."""
    existing = (
        db.query(Player)
        .filter(Player.owner_user_id == user.id, Player.linked_user_id == user.id)
        .one_or_none()
    )
    if existing:
        return existing
    player = Player(
        owner_user_id=user.id,
        name=user.name or user.username or "Me",
        linked_user_id=user.id,
    )
    ...
```

**Modify `set_game_players`:** After validating `player_ids`, ensure owner player id is in list:

```python
owner_player = ensure_owner_player(db, user)
if owner_player.id not in player_ids:
    player_ids = [owner_player.id] + [pid for pid in player_ids if pid != owner_player.id]
```

Minimum 2 players still means ≥1 opponent selected.

### Frontend

**File:** [`GamePlayersPage.tsx`](../../dev/scrabble-helper/frontend/src/pages/GamePlayersPage.tsx):
- Fetch `/api/me` for current user name
- Show read-only row: "You ({name}) — always playing"
- Checkbox list = opponents only (exclude owner player id from toggle list)
- `onContinue`: `setPlayers(gameId, [ownerPlayerId, ...selected])`
- Button enabled when `selected.length >= 1` (you + ≥1 opponent)

**Optional API:** `GET /api/players` includes `is_self: bool` when `linked_user_id == current user`

### Tests

**File:** `backend/tests/test_gameplay_qa.py` or new test:
- Create game, set players with only opponent ids → owner auto-added
- Game begins with owner in roster

---

## Commit 4: Inactivity warning (2.5h)

### Constants

```python
INACTIVITY_WARN_AFTER_SEC = 2 * 3600 + 55 * 60  # 2h 55m
INACTIVITY_END_AFTER_SEC = 3 * 3600             # 3h (optional auto-end v2)
```

### Migration `006_game_last_activity.py`

Add to `games` table:
- `last_activity_at` datetime nullable

Backfill: `last_activity_at = started_at` for active games.

### Backend

**Update in [`services.py`](../../dev/scrabble-helper/backend/app/services.py):**
- `begin_game`: set `last_activity_at = now`
- `record_turn`: set `last_activity_at = now`
- `game_state` response (used by broadcast): add fields:

```python
"last_activity_at": game.last_activity_at.isoformat() if game.last_activity_at else None,
"inactivity_warning": bool(...),  # active and idle > WARN threshold
```

**New endpoint (optional cleaner UX):**

```python
POST /api/games/{id}/ack-inactivity
# Sets last_activity_at = now without recording a turn ("Continue playing")
```

### Frontend

**File:** [`GamePlayPage.tsx`](../../dev/scrabble-helper/frontend/src/pages/GamePlayPage.tsx):
- When `state.inactivity_warning && !dismissed`: show modal
- Copy: "No turns recorded in almost 3 hours. Continue playing or end the game?"
- **Continue** → `POST ack-inactivity`, close modal
- **End game** → existing `endGame()`

Use `localStorage` key `inactivity-dismissed-{gameId}` only for same-session; server `last_activity_at` is source of truth.

### Tests

- Mock game with `last_activity_at` 3 hours ago → state includes `inactivity_warning: true`
- ack-inactivity resets warning

---

## README update

Remove or mark resolved rows in Known Issues table after ship.

---

## Out of scope

- Full `/privacy` page (Phase 3 with photos; feedback email disclosed there later)
