# Scrabble Helper

Live Scrabble scorekeeping and analytics for your games.

## Live site

- **Production:** https://scrabble-helper.fly.dev/

## Stack

- **Backend:** FastAPI, PostgreSQL, authlib (Google OIDC)
- **Frontend:** React + TypeScript + Vite
- **Deploy:** Docker on Fly.io

## Documentation

- **Releases & deploy:** [docs/RELEASE.md](docs/RELEASE.md)
- **Plans & mobile workflow:** [docs/plans/README.md](docs/plans/README.md) · [docs/MOBILE.md](docs/MOBILE.md)

## REST API

JSON API on the same host as the web app. **Base URL:** `https://scrabble-helper.fly.dev` (or your custom domain).

**Authentication:** Session cookie after login. Send cookies on every request (`curl -b cookies.txt -c cookies.txt`). Google sign-in is browser-only; for scripts and manual calls, use email/password (`POST /auth/login`). Check what is enabled with `GET /auth/config`.

**Errors:** `401` = not signed in; `403` = forbidden; `404` = missing or disabled feature; JSON body includes a `detail` field.

**Full schemas:** Interactive OpenAPI at [/docs](https://scrabble-helper.fly.dev/docs) on a running backend.

### Sign in (email/password)

```powershell
# Save session cookie for later calls
curl -c cookies.txt -X POST https://scrabble-helper.fly.dev/auth/login `
  -H "Content-Type: application/json" `
  -d '{"email":"you@example.com","password":"YourPass123"}'

curl -b cookies.txt https://scrabble-helper.fly.dev/auth/me
```

Registration (when enabled): `POST /auth/register/send-code` → `POST /auth/register/verify` (6-digit email code). Password reset: `POST /auth/password-reset/request` → `POST /auth/password-reset/confirm` (password accounts only; Google-only accounts should use Google sign-in). One account per session; signing in elsewhere may replace your session.

Sign out: `POST /auth/logout` (with cookie).

### Typical live game flow

1. **Players** — `GET /api/players`, `POST /api/players` with `{"name":"Alice"}`
2. **Create game** — `POST /api/games` with optional settings, e.g. `{"settings":{"minutes_per_turn":3,"input_mode":"points","show_live_leaderboard":true}}`
3. **Roster** — `PUT /api/games/{id}/players` with `{"player_ids":[1,2]}`
4. **Turn order** — `POST /api/games/{id}/turn-order` with `{"player_ids":[2,1]}` or `POST .../random-first`
5. **Start** — `POST /api/games/{id}/begin`
6. **Play** — `POST /api/games/{id}/turns` with `{"points":24,"word":"QUIZ","play_type":"score"}` (`play_type`: `score`, `challenge`, or `skip`); then `POST .../next-player` to advance
7. **Finish** — `POST /api/games/{id}/end`, then `POST .../finalize` with rack adjustments, e.g. `{"rack_adjustments":{"1":-12,"2":0}}`
8. **Review** — `GET /api/games/{id}` (full stats) or `GET /api/games/{id}/state` (live board)

Poll live state with `GET /api/games/{id}/state`, or connect to WebSocket `GET /api/games/{id}/watch` (cookie auth) for push updates.

### Endpoints by area

| Area | Method | Path | Purpose |
|------|--------|------|---------|
| **Health** | GET | `/health` | Liveness (`?db=1` checks database) |
| **Auth** | GET | `/auth/config` | Which login methods are enabled |
| | POST | `/auth/login` | Email/password sign-in |
| | POST | `/auth/register/send-code`, `/auth/register/verify` | Register with email verification |
| | POST | `/auth/password-reset/request`, `/auth/password-reset/confirm` | Reset password with email code |
| | GET | `/auth/me` | Current user |
| | POST | `/auth/logout` | End session |
| **Profile** | PATCH | `/api/me` | Set username |
| | POST/DELETE | `/api/me/avatar` | Upload or remove avatar |
| **Home** | GET | `/api/home` | Dashboard counts |
| **Players** | GET/POST | `/api/players` | List or create saved players |
| **Games** | GET | `/api/games?status=` | Your games (`draft`, `active`, `ending`, `completed`) |
| | GET | `/api/games/participating?status=` | Games you play in but do not own |
| | POST | `/api/games` | Create game |
| | PUT | `/api/games/{id}/players` | Set roster |
| | POST | `/api/games/{id}/turn-order`, `/random-first`, `/begin` | Setup |
| | POST | `/api/games/{id}/turns`, `/next-player` | Record play and advance |
| | POST | `/api/games/{id}/end`, `/finalize`, `/ack-inactivity`, `/abandon` | End or leave |
| | GET | `/api/games/{id}`, `/api/games/{id}/state` | Detail or live state |
| | GET/POST/DELETE | `/api/games/{id}/photos` | Game photos |
| **Stats** | GET | `/api/leaderboard?scope=` | Leaderboards (`all`, `friends`, `manual`) |
| **Dictionary** | GET | `/api/dictionary/check/{word}` | Check word against ENABLE |
| **Friends** | GET/POST/DELETE | `/api/friends`, `/api/friends/{user_id}` | List, request, remove |
| | GET | `/api/friends/requests/incoming` | Pending requests |
| | POST | `/api/friends/requests/{id}/accept`, `/deny` | Respond to request |
| | GET | `/api/users/search?q=` | Find users by username |
| **Notifications** | GET | `/api/notifications`, `/api/notifications/unread-count` | Inbox and badge |
| | POST | `/api/notifications/{id}/read`, `/dismiss`, `/accept`, `/deny` | Mark or act |
| | POST | `/api/notifications/read-all` | Mark all read |
| **Feedback** | POST | `/api/feedback` | Send bug/idea (`{"message":"...","category":"bug"}`) |

**Admin** (requires admin account): `GET /api/admin/users`, `GET /api/admin/games`, `DELETE /api/admin/games/{id}`, bulk game cleanup under `/api/admin/users/...`, feedback review under `/api/admin/feedback`. Same session cookie after admin login.

## Known Issues

_Reported by QA. Review and assign as needed._

| Date | Reporter | Area | Summary | Steps to reproduce |
|------|----------|------|---------|-------------------|
| 2026-07-09 | @haaslogan1 | Live play | **Critical:** Orphan live game blocks new games; participant stuck on owner-only End Game flow; owner sees nothing | (1) @haaslogan1 tries to start a live game with @madisonmitchellusa — blocked because she appears to be in a live game. (2) @madisonmitchellusa: open notifications → tap a live-game notification from ~4 days ago → redirected to **End game** → tap **Finalize game** → `Error: only the game owner can do this`. (3) @haaslogan1: home page shows **no** in-progress live game banner or resume link. Expected: stale/orphan games auto-complete after inactivity; participants can abandon (not finalize); both users see accurate live-game status. |
