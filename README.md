# Career Platform

A FastAPI site served at [gavinclarke.me](https://gavinclarke.me). Production
runs on Railway with PostgreSQL; local development uses SQLite.

## Local development

Local work stays on SQLite. Nothing here touches Railway.

```bash
cp .env.example .env          # DATABASE_URL=sqlite:///./career_platform.db, ENVIRONMENT=development
uv sync                       # or: python -m pip install -r requirements.txt
uv run alembic upgrade head   # migrates whatever DATABASE_URL names
uv run uvicorn app.main:create_app --factory --reload
```

The site is at `http://127.0.0.1:8000`. `/admin` is served only here: when
`ENVIRONMENT=development` and the app is not running on Railway.

Tests run on SQLite by default. Set `TEST_DATABASE_URL` to also run them
against a local Postgres:

```bash
uv run pytest
TEST_DATABASE_URL=postgresql://localhost/career_test uv run pytest
```

## Production on Railway

| Piece | Where |
|---|---|
| Project | `renewed-strength`, environment `production` |
| App | service `web`, deployed from `main` of `gclarke5/career-platform-2-` |
| Database | service `Postgres`, reached privately at `postgres.railway.internal` |
| Domains | `gavinclarke.me` (custom) and `web-production-9277a.up.railway.app` |
| DNS | Cloudflare: `@` is a CNAME to `dwaascah.up.railway.app`, DNS only (grey cloud) |
| `www` | Redirected by Cloudflare, not Railway (see below) |

Railway terminates HTTPS and forwards to Uvicorn on the port it sets in
`PORT` (8080). Uvicorn runs with `--forwarded-allow-ips="*"` so the app trusts
`X-Forwarded-Proto` and builds `https://` redirects.

### `www.gavinclarke.me`

Railway's plan allows one custom domain per service, and `gavinclarke.me` uses
it. So `www` never reaches Railway: in Cloudflare, `www` is an A record to the
placeholder `192.0.2.1`, **proxied** (orange cloud), and a redirect rule
("Redirect www to the root domain") answers every `www` request with a 301 to
`https://gavinclarke.me`, keeping the path and query string. The placeholder
address is never contacted. Don't switch `www` to DNS only, or the redirect
stops and the name points nowhere.

### Variables on `web`

| Variable | Value |
|---|---|
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` (a reference, so the password never leaves Railway) |
| `ENVIRONMENT` | `production` (turns `/admin` off) |
| `RAILPACK_START_CMD` | the start command from `railway.json` |

The app accepts `postgres://` and `postgresql://` URLs and uses psycopg 3.

### Deploys

Every push to `main` builds and deploys `web`:

1. **Build:** Railpack installs the dependencies and takes its start command
   from `RAILPACK_START_CMD`.
2. **Pre-deploy:** `alembic upgrade head` runs against Postgres. If it fails,
   the new version never serves traffic.
3. **Start:** Uvicorn with 2 workers. Railway checks `/health` before
   switching traffic.

Railway does not apply `railway.json` to this service. The pre-deploy command,
health check (`/health`, 60 s) and restart policy (on failure, 5 retries) are
set on `web` in Railway itself, and `RAILPACK_START_CMD` supplies the start
command. `railway.json` holds the same values, and `tests/test_deploy_config.py`
checks them there, so when you change one, change both.

`railway redeploy` reruns the previous deployment's settings. After changing
deploy settings, deploy the latest commit fresh (push to `main`, or "Deploy
latest commit" in the dashboard) instead.

Deploys never seed. Migrations build the schema and insert nothing, and a test
fails if one ever does. The content in Postgres was copied once from the old
VM's SQLite database with `python -m app.content_copy`, which refuses to write
into a database that already has rows.

### Changing content

Postgres is the source of truth; the local SQLite file is not.

1. Turn on the Postgres TCP proxy (Railway → `Postgres` → Settings →
   Networking), then open a shell with `railway connect Postgres`.
2. Make the change, then turn the proxy off again.
3. If you changed the profile, experience, projects or `site_meta`, update
   `app/fallback_data.py` to match.

Schema changes are ordinary Alembic migrations; merging to `main` applies them.

### Checking on it

```bash
railway status                          # services and the linked one
railway deployment list -s web          # recent deployments
railway logs -s web --latest --deployment
railway domain list -s web
```

## Fallback

If the database is unreachable, every public page still renders the profile
from `app/fallback_data.py`, and connections fail fast so pages don't hang.
`/health` reports `{"database": "unavailable", "fallback": true}` in that
state. It checks connectivity only, so `"healthy"` doesn't mean the tables
have content.

## The old Azure VM

The site used to run on an Azure VM (nginx, systemd, SQLite). No DNS record
points to it any more, but it stays up, unchanged, as the rollback: pointing
`@` back to its A record (`20.114.0.108`) restores the old host. It hasn't been
retired. See `docs/superpowers/plans/2026-10-08-railway-postgres-migration.md`
for the move and `docs/superpowers/plans/2026-10-01-operate-the-vm.md` for the
VM setup.
