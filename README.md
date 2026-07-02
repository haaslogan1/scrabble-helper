# Scrabble Helper

Live Scrabble scorekeeping and analytics for your games.

## Live site

- **Fly.io:** https://scrabble-helper.fly.dev/ (after deploy)
- **Custom domain:** https://scrabblehelper.com/ (configure DNS + `fly certs add`)

## Stack

- **Backend:** FastAPI, PostgreSQL, authlib (Google OIDC)
- **Frontend:** React + TypeScript + Vite
- **Deploy:** Docker on Fly.io

## Local development

```powershell
# Start Postgres
docker compose up -d db

# Backend
cd backend
pip install -r requirements-dev.txt
$env:DATABASE_URL="postgresql://scrabble:scrabble@localhost:5432/scrabble_helper"
$env:DEV_AUTH_BYPASS="true"
uvicorn app.main:app --reload --port 8080

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 — API requests proxy to port 8080.

## Tests

```powershell
cd backend
$env:DATABASE_URL="postgresql://scrabble:scrabble@localhost:5432/scrabble_helper"
$env:DEV_AUTH_BYPASS="true"
pytest --cov=app
```

## Deploy

Releases use **PRs → merge to `main` → automated staging + production deploy**. See [docs/RELEASE.md](docs/RELEASE.md) for the full workflow, smoke tests, and rollback.

**One-time Fly setup:**

```powershell
# Production secrets (Neon/Supabase Postgres recommended):
fly secrets set DATABASE_URL="postgresql://..." SESSION_SECRET="..." GOOGLE_CLIENT_ID="..." GOOGLE_CLIENT_SECRET="..." --app scrabble-helper
fly secrets unset DEV_AUTH_BYPASS --app scrabble-helper

# Staging app (separate DB):
fly apps create scrabble-helper-staging
fly secrets set DATABASE_URL="..." SESSION_SECRET="..." ... --app scrabble-helper-staging
```

**GitHub:** set repo secret `FLY_API_TOKEN` for automated deploys.

Manual emergency deploy: `fly deploy` (prefer the merge pipeline in normal use).

Until `DATABASE_URL` is set, `/health` and the SPA shell load; API routes need a live database.

## Google OAuth setup

1. Create OAuth credentials in [Google Cloud Console](https://console.cloud.google.com/)
2. **Authorized redirect URI:** `https://scrabble-helper.fly.dev/auth/callback/google`
3. Store credentials as **Fly secrets** (never commit to git):

```powershell
fly secrets set GOOGLE_CLIENT_ID="..." GOOGLE_CLIENT_SECRET="..." -a scrabble-helper
```

Secrets live only on Fly (`fly secrets list` shows names, not values). `.env` is gitignored for local dev.

**Security:** Do not put client IDs/secrets in `fly.toml`, source code, or GitHub. Use `fly secrets set` for production.

After Google redirects back, the app still needs `DATABASE_URL` set as a Fly secret to save user accounts (Neon/Supabase free tier). Until then, sign-in may fail at the callback step.

## Legacy family dashboard

The original import-based family site remains in the separate `scrabble2` repo.

## Basic users (email/password)

Local accounts (`provider=local`) can **register** and **sign in** on the login page alongside Google. Password policy: 10+ characters, at least one letter and one digit.

**Email verification:** New accounts must verify ownership of the email address. Registration is two steps: enter details → receive a 6-digit code by email → enter the code to finish. Uses standard SMTP (no third-party email vendor).

### SMTP (Fly secrets)

```powershell
fly secrets set `
  SMTP_HOST="smtp.gmail.com" `
  SMTP_PORT="587" `
  SMTP_USER="you@gmail.com" `
  SMTP_PASSWORD="your-app-password" `
  SMTP_FROM="you@gmail.com" `
  -a scrabble-helper
```

Gmail: use an [App Password](https://support.google.com/accounts/answer/185833) with 2FA enabled. Any SMTP server works (Outlook, self-hosted Postfix, etc.).

### Admin API

Bootstrap admin via Fly secrets (never commit):

```powershell
fly secrets set ADMIN_EMAIL="you@example.com" ADMIN_PASSWORD="YourStrongPass1" -a scrabble-helper
```

Admin endpoints (session cookie after `POST /auth/login`):

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/admin/users` | List users |
| GET | `/api/admin/games?owner_email=` | List games |
| DELETE | `/api/admin/games/{id}` | Delete one game |
| DELETE | `/api/admin/users/by-email/{email}/games` | Bulk-delete all games for a user |

Example cleanup:

```powershell
# Login as admin, then (with session cookie):
curl -X DELETE https://scrabble-helper.fly.dev/api/admin/users/by-email/haaslogan1@gmail.com/games -b cookies.txt
```

### QA agent

Say **run QA agent on scrabble-helper** or use the project skill at `.cursor/skills/scrabble-qa/SKILL.md`. The agent registers basic users, plays games via API/browser, and logs issues below. It loops until you stop it.

## Known Issues

_Reported by QA agent. Review and assign to dev agent as needed._

| Date | Reporter | Area | Summary | Steps to reproduce |
|------|----------|------|---------|-------------------|
| 2026-06-30 | Dev | Live play | No warning when a game runs 2.5+ hours | Start a game, leave it inactive (no turns) for 2.5+ hours; user should be warned the game is ending in 5 mins if they do not play a turn or acknowledge the error and press 'continue'. Currently, no prompt appears. |
| 2026-07-02 | Dev | Game setup | Must select yourself as a player before starting a game | On the player selection screen, you have to add yourself as a player to start a game. This should not be an option — it should be assumed that you are always playing, and you should only need to add the other players. |
| 2026-07-02 | Dev | Auth | Multiple concurrent sessions per user allowed | Log in as the same user from two devices at once (e.g. phone and laptop). Both sessions stay active. Expected: only one session per user is valid; logging in on a new device should show a warning like "Session exists on [mobile/computer]. That session has been logged off" and invalidate the previous session. |
