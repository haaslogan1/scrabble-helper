# Working from mobile

Use this repo on your phone to **read plans** and **kick off agent work** without a laptop.

## Read plans on mobile

1. Install the **GitHub** app (or use github.com in the browser).
2. Open `haaslogan1/scrabble-helper` → **docs/plans/**.
3. Start with [plans/README.md](plans/README.md) → [product_roadmap_2026.md](plans/product_roadmap_2026.md).

Markdown renders well in the GitHub app. Bookmark the roadmap file for quick access.

## Build / implement from mobile (Cursor)

1. **Cursor mobile** (or Cursor web) with the repo connected to GitHub.
2. Open a chat and point at a plan, e.g.  
   *“Implement Phase 2 PR1 from docs/plans/phase2_play_depth_impl.md. Follow delivery-pipeline.”*
3. The agent picks up:
   - [.cursor/rules/delivery-pipeline.mdc](../.cursor/rules/delivery-pipeline.mdc) — branch → PR → CI → merge (no direct pushes to `main`)
   - [.cursor/skills/scrabble-qa/SKILL.md](../.cursor/skills/scrabble-qa/SKILL.md) — QA loop when you ask for it
   - [docs/RELEASE.md](RELEASE.md) — deploy and rollback details

### What you can do on mobile

| Task | Mobile-friendly? | How |
|------|------------------|-----|
| Read / edit plans | Yes | GitHub app or Cursor |
| Agent implements a phase | Yes | Cursor agent + plan path in prompt |
| Open / review PRs | Yes | GitHub app |
| Merge after CI green | Yes | GitHub app (if branch protection allows) |
| Run `pytest` / `npm test` locally | No | CI runs on PR; trust green checks |
| Manual staging QA | Partial | Browser → staging URL in [RELEASE.md](RELEASE.md) |
| Fly deploy / secrets | No | Laptop only; prod deploy is automatic on merge |

### Prompt template

```text
Implement [task id] from docs/plans/phaseN_….md.
Follow .cursor/rules/delivery-pipeline.mdc: feature branch, PR, wait for CI, merge.
Do not edit plan files unless I ask.
```

## GitHub notifications (optional)

Turn on notifications for:

- **Actions** failures on `main` or your PR branches
- **Pull request** reviews and CI status

That way you see deploy/smoke failures without polling.

## Push window

Agent pushes to GitHub should happen **6:00 PM–6:00 AM local time** (see delivery-pipeline rule). You can still review plans and merge PRs any time; only **git push** from agents is windowed.

## Not in the repo (keep on laptop)

- Fly secrets and one-time bootstrap ([RELEASE.md](RELEASE.md))
- Local Postgres / `docker compose` dev stack ([README.md](../README.md))
- `.env` files and API tokens

If you need remote dev with a full shell, add **GitHub Codespaces** later (not configured today); Cursor cloud agents cover most “implement this plan” work.
