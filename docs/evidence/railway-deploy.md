# Publishing a reviewed change through Railway

Written on 2026-10-26, the day of the change.

## 1. How Railway deploys

| Setting | Value |
|---|---|
| Service | `web` in project `renewed-strength`, environment `production` |
| Source | GitHub repo `gclarke5/career-platform-2-`, branch `main` (Railway → `web` → Settings → Source) |
| Trigger | Every push to `main`, which includes merging a PR, builds and deploys automatically |
| Before serving | Pre-deploy runs `alembic upgrade head`; Railway checks `/health` before switching traffic |

**Credentials stay out of the public repo:**

- `.env` is in `.gitignore`. The tracked `.env.example` contains only local
  defaults: a SQLite path and `ENVIRONMENT=development`.
- On Railway, `DATABASE_URL` is the reference `${{Postgres.DATABASE_URL}}`,
  which Railway fills in inside the project. The password is never in Git.
- The only database URLs in the code are fake ones in tests
  (`postgresql://u:p@host:5432/db`).
- This change needed no new variables: Railway itself sets
  `RAILWAY_GIT_COMMIT_SHA`.

## 2. The change

`/health` now names the commit it's running: `"commit"` is the first 7
characters of `RAILWAY_GIT_COMMIT_SHA`, and `null` when the app isn't on
Railway. It's [PR #28](https://github.com/gclarke5/career-platform-2-/pull/28),
which changed 3 lines of `app/main.py` and added two tests.

**Verified locally before committing:**

| Check | Result |
|---|---|
| New tests run before the code existed | Both failed (`KeyError: 'commit'`), as they should |
| `uv run pytest` after the change | 62 passed on SQLite |
| `TEST_DATABASE_URL=postgresql://localhost/career_test uv run pytest` | 62 passed on Postgres |
| App run locally with `RAILWAY_GIT_COMMIT_SHA=$(git rev-parse HEAD)` | `{"status":"ok","database":"healthy","fallback":false,"commit":"afbc403"}`, matching the commit given |
| App run locally without it | `"commit":null`; homepage 200 |
| `git diff` reviewed | Only `app/main.py` and `tests/test_health_checks.py` changed |

## 3. From commit to live site

| Step | Evidence |
|---|---|
| Feature commit | `2069c80` "feat: /health names the deployed commit", 2026-10-26 12:29 PDT |
| Merged to `main` | Merge commit `bbb47d8` (PR #28), 12:30:35 PDT |
| Railway deployment | `49d3c114-d85a-4bfe-86c8-92494d81e31b`, created 19:30:37 UTC (12:30 PDT) from `main`, commit `bbb47d8`, status `SUCCESS` |
| Deploy log | Pre-deploy Alembic ran against Postgres (`PostgresqlImpl`), then `Uvicorn running on http://0.0.0.0:8080` and `Application startup complete` for both workers |
| Live at the domain | `curl -s https://gavinclarke.me/health` at 19:31:42 UTC → `{"status":"ok","database":"healthy","fallback":false,"commit":"bbb47d8"}` |

About a minute after the merge, the domain reported `bbb47d8`, the same commit
as the Railway deployment. Before this deploy, `/health` on the previous
deployment (`79584610…`, commit `afbc403`) returned
`{"status":"ok","database":"healthy","fallback":false}`, with no `commit` at
all.

The commit is the merge commit, not the feature commit, because Railway
deploys whatever `main` points to after the merge.

## 4. Rolling back

How to restore a previous working version, for both code and database
changes, is in the README's [Rollback](../../README.md#rollback) section. Two
parts of it were tested on 2026-10-26, without touching production:

- **Old code against a newer schema:**
  - code from before migration `d4a8f1c2e7b9` (commit `e1bcbd4`), run against a
    database at that revision, failed with
    `Can't locate revision identified by 'd4a8f1c2e7b9'`;
  - after `alembic downgrade c7e1a9d3f2b8` with the current code, the old code's
    `alembic upgrade head` succeeded.

  That's why the README downgrades before rolling code back.
- **Restoring content from a backup:**
  - the 2026-10-26 backup was copied into a local Postgres;
  - one project was deliberately broken;
  - the tables were emptied, and the backup copied back in.

  The project came back as it was, and a new row got the next free id (8).
