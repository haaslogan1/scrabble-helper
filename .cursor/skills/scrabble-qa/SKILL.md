---
name: scrabble-qa
description: >-
  Continuous QA for scrabble-helper. Register basic users, play extensive games
  via API/browser, log issues to README Known Issues, and loop until the user stops.
---

# Scrabble Helper QA Agent

## When to use

Apply when the user says **run QA**, **QA agent**, **gameplay testing**, or wants automated scrabble-helper testing without manual steps.

## QA agent job

1. Create a non-SSO user (basic user) and play a ton of games.
2. Report issues to the README in **Known Issues** section.
3. You will review issues later and get a dev agent to work if necessary.
4. Return to step 1.

**Do not stop until you stop the QA agent.**

## Rules

- **Report only** — do not fix bugs during QA runs.
- Authenticate as a **basic user** (`POST /auth/register` or `POST /auth/login`). Never use Google SSO or `DEV_AUTH_BYPASS`.
- Target: `https://scrabble-helper.fly.dev` unless the user specifies local (`http://localhost:8080`).
- Credentials: register `qa+<timestamp>@test.local` with password meeting policy (10+ chars, letter + digit), or use `QA_BASIC_EMAIL` / `QA_BASIC_PASSWORD` env if set.
- Vary scenarios each loop: player counts (2–4), points vs words mode, completed vs in-progress games, invalid point submissions, challenge/skip, end/finalize flow.

## Gameplay checklist

Use [`backend/tests/qa_gameplay.py`](backend/tests/qa_gameplay.py) helpers when testing via API, or mirror the same flows in the browser.

| Area | What to exercise |
|------|------------------|
| Auth | Register, login, logout, session |
| Roster | Create players |
| Setup | Settings, attach players, begin |
| Live play | Valid/invalid points, challenge, skip, standings, auto-advance |
| End game | Rack adjustments, finalize, winner |
| History | Completed list, game detail |
| Leaderboard | User-scoped stats |

## Reporting issues

Append rows to **Known Issues** in [`README.md`](README.md):

| Date | Reporter | Area | Summary | Steps to reproduce |
|------|----------|------|---------|-------------------|

- One row per distinct issue; skip duplicates already listed.
- Include basic user email (not password), game id if relevant, exact steps.
- Optional severity: blocker / major / minor.

## API quick reference

```http
POST /auth/register  {"email","password","name"}
POST /auth/login     {"email","password"}
POST /api/players    {"name"}
POST /api/games      {"settings":{...}}
PUT  /api/games/{id}/players  {"player_ids":[...]}
POST /api/games/{id}/begin
POST /api/games/{id}/turns    {"points":12,"play_type":"score"}
POST /api/games/{id}/end
POST /api/games/{id}/finalize {"rack_adjustments":{...}}
```

Use `credentials: 'include'` on fetch, or `TestClient` session cookies after login.

## Loop

After each batch of games, update Known Issues if needed, then return to step 1 (new or same basic user). Only stop when the user explicitly ends the session.
