---
name: Phase 2 — Play Depth (implementation)
phase: 2
overview: "Canonical Phase 2 plan: rules + dictionary pages (separate PRs), local ENABLE word list, optional word tracking later. Parent: product_roadmap_2026."
prerequisites: [phase1]
blocks: [phase3]
estimated_duration: 2-3 weeks
todos:
  - id: pr1-rules
    content: "PR 1 (phase2/rules-page): Vitest, GameReferenceLayout, rulesContent, RulesPage, /game/rules, play toolbar, frontend tests"
    status: in_progress
  - id: pr2-dictionary
    content: "PR 2 (phase2/dictionary): ENABLE + dictionary.py + internal check endpoint + backend tests + DictionaryPage"
    status: pending
  - id: pr2-word-tracking
    content: "PR 3 (future): input_mode toggle, word field on turn submit, optional validation"
    status: pending
isProject: false
---

# Phase 2 — Play Depth (implementation)

**Roadmap (high-level):** [product_roadmap_2026_36ec752e.plan.md](product_roadmap_2026_36ec752e.plan.md)

**Supersedes:** ~~rules_dictionary_pages_4b14257e.plan.md~~, ~~rules_dict_split_prs_b691a996.plan.md~~ (merged here).

---

## Design decisions (final)

| Topic | Decision |
|-------|----------|
| Routes | Static `/game/rules` and `/game/dictionary` (before `/game/:id/...` in App.tsx) |
| Back to game | `location.state.returnTo` → `?gameId=` → `/` |
| Dictionary data | **Local ENABLE** (`backend/data/enable1.txt` → frozenset). No external APIs. |
| Dictionary UX | Exact-word challenge lookup only — no prefix search |
| Definitions | Out of scope (v2) |
| Delivery | **Two PRs** (rules, then dictionary); word tracking is a third PR later |

---

## PR 1: Rules page

**Branch:** `phase2/rules-page` | **Testing focus:** frontend (Vitest + RTL)

### Files

- Vitest setup: [`frontend/package.json`](../../dev/scrabble-helper/frontend/package.json), `frontend/vite.config.ts`, [`.github/workflows/ci.yml`](../../dev/scrabble-helper/.github/workflows/ci.yml)
- `frontend/src/hooks/useGameReturnTo.ts`
- `frontend/src/components/GameReferenceLayout.tsx`
- `frontend/src/content/rulesContent.ts` — Goal, Turns, Bingo, Challenges, Dictionary (challenge-only), End
- `frontend/src/pages/RulesPage.tsx`
- [`frontend/src/App.tsx`](../../dev/scrabble-helper/frontend/src/App.tsx) — route `/game/rules`
- [`frontend/src/pages/GamePlayPage.tsx`](../../dev/scrabble-helper/frontend/src/pages/GamePlayPage.tsx) — Rules toolbar link only

### Frontend tests

- `useGameReturnTo.test.ts` — state, query param, home fallback
- `rulesContent.test.ts` — section ids, dictionary anti-cheating copy, official URL
- `GameReferenceLayout.test.tsx`, `RulesPage.test.tsx`

No backend changes.

---

## PR 2: Dictionary

**Branch:** `phase2/dictionary` | **Testing focus:** backend (pytest)

### Files

- `backend/data/enable1.txt`, `backend/data/README.md`
- `backend/app/dictionary.py` — `load_word_set`, `normalize_word`, `is_valid_word`
- [`backend/app/main.py`](../../dev/scrabble-helper/backend/app/main.py) — `GET /api/dictionary/check/{word}` (auth, wraps local ENABLE)
- `backend/tests/test_dictionary.py` + fixture files
- `frontend/src/pages/DictionaryPage.tsx`, route, `api.ts` client, play **Check word** link

### Backend tests (ship gate)

1. Full `enable1.txt` integrity scan
2. Fixture files 100% pass
3. ~50 parametrized valid + invalid
4. Normalization edge cases
5. API integration (auth required)

### Frontend tests (smoke)

- `DictionaryPage.test.tsx` — callout, empty submit, mocked valid/invalid result

---

## PR 3 (future): Word tracking

- `GameSettingsPage` — `input_mode: "word"` toggle
- `GamePlayPage` — optional word field on turn submit
- Optional `validate_words` in `services.py`

---

## After PR 1 + PR 2 merged

Update [product_roadmap_2026_36ec752e.plan.md](product_roadmap_2026_36ec752e.plan.md): mark phase2-rules/dictionary done; add phase2-word-tracking pending; fix Phase 2 summary bullets.
