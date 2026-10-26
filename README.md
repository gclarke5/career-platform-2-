# Career Platform

A FastAPI site served at [gavinclarke.me](https://gavinclarke.me). Production
runs on Railway with PostgreSQL; local development uses SQLite. See
[`docs/database-choice.md`](docs/database-choice.md) for why.

## Email

Mail for `@gavinclarke.me` goes to Zoho Mail (`career-platform@gavinclarke.me`),
with MX, SPF, DKIM and DMARC records in Cloudflare. The tests and records are
in [`docs/evidence/ex06.md`](docs/evidence/ex06.md), and the header analysis
is in [`docs/evidence/zoho-header-check.md`](docs/evidence/zoho-header-check.md).

## Analytics

Google Analytics 4 (`G-FVPBZ69VK0`, set by the `GA_MEASUREMENT_ID` variable)
loads only after a visitor accepts the consent banner (`static/js/consent.js`).
Setup, verification and what the events show are in
[`docs/evidence/analytics.md`](docs/evidence/analytics.md).

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

The move from the Azure VM is planned in
[`docs/superpowers/plans/2026-10-08-railway-postgres-migration.md`](docs/superpowers/plans/2026-10-08-railway-postgres-migration.md),
against the project spec in
[`docs/superpowers/specs/resume-career-platform-spec.md`](docs/superpowers/specs/resume-career-platform-spec.md).
[`docs/evidence/railway-migration.md`](docs/evidence/railway-migration.md)
records the data comparison, cutover, rollback and who manages what.

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

1. Open a shell with `railway connect Postgres`. It reaches the database
   through an encrypted SSH tunnel, so Postgres never needs public access
   (leave Railway → `Postgres` → Settings → Networking → Public access off).
   The tunnel needs an SSH key registered with Railway. This laptop's key is
   registered as `gavin-laptop`; on another machine, run
   `railway ssh keys add` once first (`railway ssh keys list` shows them).
2. Make the change in a transaction (`BEGIN;` … `COMMIT;`). The site shows it
   on the next request, with no redeploy.
3. If you changed the profile, experience or `site_meta`, update
   `app/fallback_data.py` to match. Projects have no fallback copy.

Schema changes are ordinary Alembic migrations; merging to `main` applies them.

### Checking on it

```bash
railway status                          # services and the linked one
railway deployment list -s web          # recent deployments
railway logs -s web --latest --deployment
railway domain list -s web
curl -s https://gavinclarke.me/health   # "commit" is the short SHA that's live
```

## Rollback

Code and data roll back separately. Redeploying an old version restores the
code only: it never undoes a migration or a content edit.

### Before any risky change: back up the data

Railway's Trial has no built-in Postgres backups, so take one yourself. This
copies everything in Postgres into a new SQLite file, without changing
Postgres:

```bash
B=../railway-move/postgres-backup-$(date +%F).db      # outside the repo; a new name each time
railway connect Postgres --tunnel-only --port 15432 &  # private tunnel; stop it with: kill %1
DATABASE_URL=sqlite:///$B uv run alembic upgrade head
railway run --service Postgres -- sh -c 'TARGET_DATABASE_URL=sqlite:///'"$B"' \
  .venv/bin/python -m app.content_copy "postgresql+psycopg://$PGUSER:$PGPASSWORD@127.0.0.1:15432/$PGDATABASE"'
sqlite3 -readonly $B "pragma integrity_check; select version_num from alembic_version"
```

The password stays inside the single-quoted `sh -c`, so it's never printed.
The copy refuses to write into a file that already has rows.

### Application code (no migration involved)

1. **Find the last good version:** `railway deployment list -s web` lists
   deployments with their commits. `/health`'s `"commit"` shows which one is
   live now.
2. **Revert it in Git (preferred):** `git revert <bad commit>` on a branch,
   run the tests, open a PR and merge it. Railway deploys the revert like any
   other change, and `main` matches what's live again.
3. **Faster, while the revert is prepared:** Railway dashboard → `web` →
   Deployments → the last good deployment → ⋮ → **Rollback**. This puts that
   build back without touching Git, so follow up with the revert, or the next
   push to `main` brings the bad code back. If an old deployment doesn't
   offer Rollback, use the revert.
4. **Check:** `/health`'s `"commit"` shows the good commit, and the pages that
   broke work again.

Don't use `railway redeploy`: it reruns the *latest* deployment, not an older
one.

### Schema changes (a migration was involved)

Old code can't start against a newer schema. Railway's pre-deploy step
(`alembic upgrade head`) fails with `Can't locate revision identified by '…'`,
because the old code doesn't have the newer migration file, and the deploy
stops before serving. So downgrade the database **first, using the current
code**, which still has the migration's `downgrade()`:

1. **Back up** (above). A downgrade can drop columns or tables, and the data
   in them.
2. **Find the target revision:** look up the old commit's newest file in
   `migrations/versions/` and note its revision ID.
3. **Downgrade through the tunnel:**

   ```bash
   railway connect Postgres --tunnel-only --port 15432 &
   railway run --service Postgres -- sh -c 'DATABASE_URL="postgresql+psycopg://$PGUSER:$PGPASSWORD@127.0.0.1:15432/$PGDATABASE" \
     .venv/bin/alembic downgrade <old revision>'
   ```

4. **Roll the code back** as in "Application code" above. The pre-deploy step
   now finds the database already at the old code's head.
5. **Check:** `/health` is healthy with `"fallback": false`, and the pages
   render their content.

If the migration only added something the old code ignores (a new nullable
column or table), you can also leave the database alone. Roll back by
reverting only the code that uses it, and keep the migration.

### Content (a bad edit in Postgres)

- **One row or a few:** fix them in `railway connect Postgres`, inside
  `BEGIN;` … `COMMIT;`, using the backup file as the reference
  (`sqlite3 -readonly <backup> "select … "`).
- **Everything, from a backup:** empty the content tables and copy the backup
  back in. The schema must already be at the backup's revision (`select
  version_num from alembic_version` on both):

  ```bash
  railway connect Postgres --tunnel-only --port 15432 &
  railway run --service Postgres -- sh -c 'psql "postgresql://$PGUSER:$PGPASSWORD@127.0.0.1:15432/$PGDATABASE" -c \
    "TRUNCATE profiles, experiences, projects, skills, education, certifications, links, site_meta, volunteer_work RESTART IDENTITY;"'
  railway run --service Postgres -- sh -c 'TARGET_DATABASE_URL="postgresql://$PGUSER:$PGPASSWORD@127.0.0.1:15432/$PGDATABASE" \
    .venv/bin/python -m app.content_copy sqlite:///../railway-move/postgres-backup-YYYY-MM-DD.db'
  ```

  Between the `TRUNCATE` and the copy, pages say "Projects temporarily
  unavailable" or "No projects yet", and the profile shows the fallback. The
  copy resets the id sequences, so new rows still get fresh ids. This restore
  was tested on a local Postgres on 2026-10-26.

## Fallback

If the database is unreachable, every public page still renders the profile
from `app/fallback_data.py`, and connections fail fast so pages don't hang.
Projects have no fallback: `/`, `/projects` and `/projects/<slug>` say
"Projects temporarily unavailable" and return **503**, and the next request
after the database recovers shows them again, with no restart. An empty
`projects` table shows "No projects yet" with a 200. `/health` reports `{"database": "unavailable", "fallback": true}` in that
state. It checks connectivity only, so `"healthy"` doesn't mean the tables
have content.

## The old Azure VM

The site used to run on an Azure VM, `vm-career-platform` in
`rg-career-platform` (nginx, systemd, SQLite). No DNS record points to it any
more. It is **deallocated on purpose**: it isn't deleted, and its disk, its
SQLite data and its static IP (`20.114.0.108`) are kept, but it serves nothing
until it is started. An auto-shutdown schedule also turns it off at 19:00
Pacific every day. The disk and IP still cost a little each month; see
[`docs/costs.md`](docs/costs.md).

**As of 2026-10-26 the Azure free-trial subscription is disabled and read-only**,
so `az vm start` is refused and the steps below can't run until it is
re-enabled. See [`docs/evidence/azure-vm.md`](docs/evidence/azure-vm.md) for
how the VM ran.

nginx only answers for `gavinclarke.me`, so a request to the bare IP gets a
404. To roll back to the VM:

1. Start it, and turn off auto-shutdown so it stays up:

   ```bash
   az vm start -g rg-career-platform -n vm-career-platform
   az vm auto-shutdown -g rg-career-platform -n vm-career-platform --off
   ```

2. Check that it serves the site before moving any traffic. Expect
   `Server: nginx/1.24.0 (Ubuntu)` and `"fallback": false`:

   ```bash
   curl -sI --resolve gavinclarke.me:443:20.114.0.108 https://gavinclarke.me/ | grep -i ^server
   curl -s --resolve gavinclarke.me:443:20.114.0.108 https://gavinclarke.me/health
   ```

   Certbot only renews the VM's certificate while the VM is running. If
   `curl` reports a certificate error, SSH in and run `sudo certbot renew`.
   The SSH rule only allows one home IP, so from anywhere else you'll need a
   temporary rule (see `docs/evidence/ex03.md`, section 4).

3. In Cloudflare, change `@` from the CNAME to an A record for `20.114.0.108`,
   DNS only (grey cloud).

The VM has the content as it was on the day of the move. Anything changed in
Postgres since then isn't on it.

To stop it again, deallocate it. `--off` above deletes the auto-shutdown
schedule, so set it again too (the CLI takes UTC: `0200` is 19:00 Pacific
daylight time):

```bash
az vm deallocate -g rg-career-platform -n vm-career-platform
az vm auto-shutdown -g rg-career-platform -n vm-career-platform --time 0200
```

See `docs/superpowers/plans/2026-10-08-railway-postgres-migration.md` for the
move and `docs/superpowers/plans/2026-10-01-operate-the-vm.md` for the VM
setup.
