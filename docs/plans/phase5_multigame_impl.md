---
name: Phase 5 — Multi-Game (implementation)
phase: 5
overview: Optional research sprint then game-type abstraction to support non-Scrabble scorekeeping games. Defer until after mobile or after growth per product choice.
prerequisites: [phase4]
blocks: []
estimated_duration: 4-12 weeks (research + implementation)
todos:
  - id: p5-research-doc
    content: "Deliverable 1: docs/MULTI_GAME_RESEARCH.md with game candidates + legal review"
    status: pending
  - id: p5-spec
    content: "Deliverable 2: Approved game_type spec (user sign-off before code)"
    status: pending
  - id: p5-schema
    content: "Commit 1: game_type_slug migration + backfill scrabble"
    status: pending
  - id: p5-services
    content: "Commit 2: Turn recording strategy pattern per game type"
    status: pending
  - id: p5-frontend
    content: "Commit 3: Game type picker + conditional play/settings UI"
    status: pending
  - id: p5-stats
    content: "Commit 4: Leaderboard + stats filter by game type"
    status: pending
isProject: false
---

# Phase 5 — Multi-Game Generalization: Low-Level Implementation Plan

**Roadmap context:** [Product Roadmap 2026](product_roadmap_2026_36ec752e.plan.md) → Phase 5 (optional)

**Priority covered:** #6 Multi-game generalization

**Depends on:** [Phase 4](phase4_mobile_impl.plan.md) (recommended minimum)

**Product note:** Can run **after** [Phase 6 Growth](phase6_growth_impl.plan.md) if marketing Scrabble-first.

---

## Gate: no code until spec approved

This phase starts with **research deliverables only**. Implementation commits are blocked until user reviews and approves `docs/MULTI_GAME_SPEC.md`.

---

## Deliverable 1: Research document

**New file:** `docs/MULTI_GAME_RESEARCH.md`

### Section 1 — Candidate games

Evaluate games with similar **turn-based scoring** model:

| Game | Turn structure | Word tracking? | Fit score |
|------|----------------|----------------|-----------|
| Scrabble (baseline) | rotating turns | yes | shipped |
| Bananagrams | simultaneous / rounds? | words | research |
| Words with Friends | async turns | yes | research |
| Boggle / Rummikub / custom | varies | | |

For each: score entry UX, win condition, timer needs, dictionary relevance.

### Section 2 — Legal / branding

- "Scrabble" is Hasbro trademark — app name marketing vs game type label
- Positioning: **"Scrabble Helper"** app with future **"other word games"** templates
- NASPA/word list licensing impact per game type

### Section 3 — Technical gap analysis

Map current code assumptions:

| Area | Scrabble-specific today | Generalization |
|------|-------------------------|----------------|
| [`services.record_turn`](../../dev/scrabble-helper/backend/app/services.py) | score/challenge/skip | pluggable `PlayType` set |
| [`GamePlayPage`](../../dev/scrabble-helper/frontend/src/pages/GamePlayPage.tsx) | points input | game-type component registry |
| [`rulesContent.ts`](../../dev/scrabble-helper/frontend/src/content/rulesContent.ts) | Scrabble only | per-type rules module |
| Dictionary | Scrabble list | per-type or disabled |
| Leaderboard [`stats.py`](../../dev/scrabble-helper/backend/app/stats.py) | all games one pool | filter by `game_type_slug` |
| [`friends.validate_linked_players_for_live`](../../dev/scrabble-helper/backend/app/friends.py) | one live game | unchanged initially |

### Section 4 — Migration impact

- Existing games: all `game_type_slug = 'scrabble'`
- No user-facing change for historical data

### Section 5 — Recommendation

Pick **1–2 pilot types** for v1 (e.g. `scrabble` + `generic-points` house game), not 10 games at once.

---

## Deliverable 2: Approved spec (`docs/MULTI_GAME_SPEC.md`)

Template sections:

1. **Game type registry** — slug, display name, icon
2. **Settings schema** per type (JSON Schema)
3. **Play UI component** mapping
4. **API changes** — breaking vs additive
5. **Rollout** — feature flag `MULTI_GAME_ENABLED`

**Sign-off:** User comments "approved" on plan or spec PR before Commit 1.

---

## Commit 1: Schema

### Migration `008_game_type_slug.py`

```python
op.add_column("games", sa.Column("game_type_slug", sa.String(50), nullable=False, server_default="scrabble"))
op.alter_column("games", "game_type_slug", server_default=None)
```

### Model

**File:** [`backend/app/models.py`](../../dev/scrabble-helper/backend/app/models.py):

```python
class Game:
    game_type_slug: Mapped[str] = mapped_column(String(50), default="scrabble", nullable=False)
```

### Game types registry

**New:** `backend/app/game_types/__init__.py`

```python
@dataclass
class GameTypeDef:
    slug: str
    name: str
    default_settings: dict
    settings_schema: dict  # JSON Schema

REGISTRY: dict[str, GameTypeDef] = {
    "scrabble": GameTypeDef(...),
    "generic": GameTypeDef(...),  # points-only, no dictionary
}
```

---

## Commit 2: Service layer refactor

**New:** `backend/app/game_types/scrabble.py` — move Scrabble-specific turn logic from `services.py`

```python
class GameEngine(Protocol):
    def validate_turn(self, game: Game, body: TurnRecord) -> None: ...
    def apply_turn(self, db: Session, game: Game, body: TurnRecord) -> None: ...

def get_engine(slug: str) -> GameEngine: ...
```

**File:** [`services.py`](../../dev/scrabble-helper/backend/app/services.py):
- `create_game(..., game_type_slug: str = "scrabble")`
- `record_turn` delegates to `get_engine(game.game_type_slug)`

**Tests:** Existing gameplay tests must pass unchanged for Scrabble slug.

---

## Commit 3: Frontend

### Game creation

**File:** [`GameSettingsPage.tsx`](../../dev/scrabble-helper/frontend/src/pages/GameSettingsPage.tsx):

- Step 0 or top of form: game type tiles (only enabled types)
- Conditional settings fields from schema

**New:** `frontend/src/gameTypes/registry.ts`

```typescript
export const GAME_TYPES = {
  scrabble: { label: "Scrabble", PlayUI: ScrabblePlayUI, SettingsFields: ScrabbleSettings },
  generic: { label: "Custom scoring", PlayUI: GenericPlayUI, ... },
};
```

**File:** [`GamePlayPage.tsx`](../../dev/scrabble-helper/frontend/src/pages/GamePlayPage.tsx) — render `GAME_TYPES[state.game_type_slug].PlayUI` or lazy import.

### Rules route

Generalize: `/game/:id/rules` loads rules by `game_type_slug`.

---

## Commit 4: Stats + copy

**File:** [`backend/app/stats.py`](../../dev/scrabble-helper/backend/app/stats.py):
- `GET /api/leaderboard?scope=all&game_type=scrabble`

**Frontend:** Leaderboard filter dropdown; games list badge per type.

**Notifications:** Generic copy ("Live game started" vs "Scrabble game started").

---

## Acceptance criteria

- [ ] Research doc complete and spec approved by user
- [ ] All existing Scrabble games behave identically
- [ ] At least one non-Scrabble type creatable end-to-end
- [ ] Leaderboard can filter by game type
- [ ] Mobile apps work for new type (Capacitor uses same SPA)

---

## Risk register

| Risk | Mitigation |
|------|------------|
| Scope explosion | Max 2 new types in v1 |
| Trademark | Generic labels in UI ("Word game", not competitor names) |
| Double refactor | Phase 5 only after Phases 0–4 stable |

---

## Out of scope

- Real-time multiplayer turn submission by linked friends (owner-only turns today)
- Game-type-specific photo layouts
- Per-game monetization
