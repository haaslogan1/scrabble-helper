# Release process

## PR workflow (solo repo)

1. Create a feature branch: `phaseN/short-task-name`
2. Commit focused changes (one task per commit where possible)
3. Push the branch
4. Open a PR targeting `main`: `gh pr create`
5. Wait for **CI** (`.github/workflows/ci.yml`) to pass on the PR
6. Merge when CI is green: `gh pr merge --merge --delete-branch`

**Solo repo note:** GitHub does not allow `gh pr review --approve` on your own PR (API error: *Review Can not approve your own pull request*). That is normal. You do not need an approval review to merge unless branch protection requires a reviewer other than you. For this repo, **CI passing on the PR is the gate** — then merge.

**GitHub settings (optional):** On `main`, branch protection can require the **ci / test** status check. Do **not** require approving reviews if you are the only contributor (you cannot approve your own PR).

## Deploy flow (automatic prod)

After merge to `main`:

1. **CI** runs on `main`
2. **Deploy workflow** (`.github/workflows/deploy.yml`) runs when CI succeeds
3. Deploy **staging** (`scrabble-helper-staging`)
4. **Smoke staging** — failure stops the workflow; prod is not updated
5. Deploy **production** (canary strategy)
6. **Smoke production** — on failure, **auto-rollback** to the previous release image

There is **no manual prod approval** until Phase 6 (SEO/marketing go-live).

## Staging bootstrap (one-time)

```powershell
fly apps create scrabble-helper-staging
fly secrets set DATABASE_URL="..." SESSION_SECRET="..." GOOGLE_CLIENT_ID="..." GOOGLE_CLIENT_SECRET="..." --app scrabble-helper-staging
fly deploy --config fly.staging.toml --app scrabble-helper-staging
```

Use a **separate Postgres** instance for staging (e.g. Neon). Do not commit secrets.

Staging URL: https://scrabble-helper-staging.fly.dev

Production URL: https://scrabble-helper.fly.dev

## GitHub secrets

| Secret | Purpose |
|--------|---------|
| `FLY_API_TOKEN` | Deploy from GitHub Actions (`fly tokens create deploy`) |
| `STAGING_SMOKE_EMAIL` | Optional: deep smoke on staging |
| `STAGING_SMOKE_PASSWORD` | Optional: deep smoke on staging |

## Manual rollback

```powershell
fly releases list -a scrabble-helper
fly deploy --image <previous-image-ref> -a scrabble-helper --strategy immediate
```

## Staging-only redeploy

Use **Actions → deploy → Run workflow** with target `staging` (does not promote to prod).

## Manual QA checklist (supplement to smoke)

After a significant release, manually verify on staging:

- [ ] Login (Google or email/password)
- [ ] Start game → record turn → end game → view detail
- [ ] Light/dark theme toggle

## Tier 1 limitations

Post-deploy smoke checks:

- `/health`, `/health?db=1`, SPA shell at `/`
- Optional `--deep`: login + `/api/me` + `/api/home`

Smoke does **not** cover every user path. Deferred: Sentry, error-rate rollback, live gameplay QA in CI.

## Phase 6

Manual prod approval via GitHub `production` Environment will be re-enabled at public go-live.
