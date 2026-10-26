# Career Platform

**Live at [https://gavinclarke.me](https://gavinclarke.me).**

My personal career site, built for a class project. Recruiters and hiring
managers use it to see who I am, which analyst roles I'm aiming for (finance,
or operations and supply chain), my resume, and project write-ups, and to
contact me. It's a FastAPI app that reads its profile and projects from a
database. Production runs on Railway with PostgreSQL; local development uses
SQLite ([why](docs/database-choice.md)).

The site started on an Azure VM (2026-10-08 to 2026-10-13) and moved to
Railway on 2026-10-13. Email is Zoho Mail, DNS is Cloudflare, and analytics is
Google Analytics 4. All the evidence is indexed in
[`docs/project-1-submission.md`](docs/project-1-submission.md).

Contents:
- [Architecture](#architecture)
- Setting up and running it:
  - [Local development](#local-development)
  - [Production on Railway](#production-on-railway)
  - [Rollback](#rollback)
- What happened:
  - [The migration](#how-the-migration-preserved-the-data)
  - [Decisions](#decisions)
  - [Investigated failures](#investigated-failures)
  - [Limitations](#remaining-limitations)
- Upkeep and looking back:
  - [Costs and cleanup](#costs-and-cleanup)
  - [Reflection](#reflection)

## Architecture

### Now: Railway (since 2026-10-13)

```mermaid
flowchart LR
  B["Visitor's browser"]
  subgraph CF["Cloudflare (authoritative DNS)"]
    DNS["gavinclarke.me: CNAME to Railway, DNS only<br/>www: proxied placeholder"]
    RED["Cloudflare edge<br/>redirect rule: 301 to https://gavinclarke.me"]
  end
  subgraph RW["Railway, US East (iad), project renewed-strength"]
    EDGE["Railway edge<br/>HTTPS :443, Let's Encrypt cert<br/>HTTP :80 redirects to HTTPS"]
    WEB["web service<br/>uvicorn, 2 workers, HTTP :8080"]
    PG[("Postgres 18 service<br/>postgres.railway.internal:5432<br/>private network only")]
  end
  GH["GitHub<br/>gclarke5/career-platform-2-, main"]
  GA["Google Analytics 4<br/>googletagmanager.com, google-analytics.com"]
  B -- "DNS :53" --> DNS
  B -- "HTTPS :443 gavinclarke.me" --> EDGE
  B -- "HTTP :80 / HTTPS :443 www" --> RED
  EDGE -- "HTTP :8080 + X-Forwarded-Proto" --> WEB
  WEB -- "SQL :5432" --> PG
  GH -- "push to main: build, alembic upgrade, deploy" --> WEB
  B -. "HTTPS :443, only after Accept:<br/>gtag.js, then /g/collect events" .-> GA
```

- **A page request:**
  1. The browser asks Cloudflare for `gavinclarke.me`. Cloudflare answers
     with Railway's address, because the record is DNS only.
  2. The browser opens HTTPS on port 443 to Railway's edge, which holds the
     certificate.
  3. The edge forwards plain HTTP to uvicorn on port 8080 inside Railway.
  4. The app reads Postgres over Railway's private network. Postgres has no
     public address.
- **`www`:** Cloudflare's own edge answers it with a 301 redirect, so `www`
  traffic never reaches Railway.
- **Analytics:** only after the visitor accepts the banner, the browser itself
  sends events to Google, never through Railway
  ([details](docs/evidence/analytics.md)).

### Before: Azure VM (2026-10-08 to 2026-10-13)

```mermaid
flowchart LR
  B["Visitor's browser"]
  ME["My laptop<br/>99.7.122.53"]
  subgraph CF["Cloudflare (authoritative DNS)"]
    DNS["gavinclarke.me: A 20.114.0.108, DNS only"]
  end
  subgraph AZ["Azure, West US 2, rg-career-platform"]
    NSG["NSG vm-career-platform-nsg<br/>22 from 99.7.122.53/32 only<br/>80, 443 from anywhere"]
    subgraph VM["vm-career-platform, Ubuntu 24.04<br/>public 20.114.0.108, private 172.16.0.4"]
      NGX["nginx :80, :443<br/>Certbot cert, 80 redirects to HTTPS<br/>/admin returns 404"]
      UV["uvicorn, 2 workers, systemd<br/>127.0.0.1:8000 only"]
      DB[("SQLite file<br/>~/career-platform-data/career_platform.db")]
    end
  end
  GH["GitHub"]
  GA["Google Analytics 4"]
  B -- "DNS :53" --> DNS
  B -- "HTTP :80 / HTTPS :443" --> NSG --> NGX
  NGX -- "HTTP 127.0.0.1:8000" --> UV
  UV -- "file read" --> DB
  ME -- "SSH :22, key login" --> NSG
  UV -. "git pull over HTTPS :443" .-> GH
  B -. "HTTPS :443, only after Accept" .-> GA
```

On the VM, I ran everything myself:
- nginx was the only public entry point;
- the app listened only on `127.0.0.1`;
- the database was a file on the VM's disk, with no network port;
- I deployed code by SSHing in, running `git pull`, then
  `sudo systemctl restart career-platform`.

Details are in [`docs/evidence/azure-vm.md`](docs/evidence/azure-vm.md).

### Email (Zoho Mail)

```mermaid
flowchart LR
  S["Sender's mail server<br/>(for example iCloud)"]
  CF["Cloudflare DNS<br/>MX, SPF, DKIM, DMARC records"]
  ZIN["mx.zoho.com<br/>(mx2, mx3 as backups)"]
  BOX["Zoho mailbox<br/>career-platform@gavinclarke.me"]
  ME["Me, Zoho webmail<br/>HTTPS :443"]
  ZOUT["Zoho outbound server<br/>(sender5-of-o52.zoho.com)"]
  R["Recipient's mail server"]
  S -- "MX lookup :53" --> CF
  S -- "SMTP :25" --> ZIN --> BOX
  ME --> BOX
  BOX -- "send, DKIM-signed (s=zmail)" --> ZOUT
  ZOUT -- "SMTP :25" --> R
  R -- "check SPF, DKIM, DMARC :53" --> CF
```

- **Incoming:** a sender's server looks up the MX records in Cloudflare and
  delivers over SMTP to Zoho.
- **Outgoing:** Zoho signs each message with my DKIM key and sends it. The
  receiving server then checks SPF, DKIM and DMARC against my DNS records.

Mail doesn't involve the VM or Railway at all, so it kept working through the
move. The tests and records are in [`docs/evidence/ex06.md`](docs/evidence/ex06.md),
and the header analysis is in
[`docs/evidence/zoho-header-check.md`](docs/evidence/zoho-header-check.md).

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
Postgres since then isn't on it, so copy Postgres back to the VM before step 3
(see the rollback in [`docs/evidence/railway-migration.md`](docs/evidence/railway-migration.md),
section 6).

To stop it again, deallocate it. `--off` above deletes the auto-shutdown
schedule, so set it again too (the CLI takes UTC: `0200` is 19:00 Pacific
daylight time):

```bash
az vm deallocate -g rg-career-platform -n vm-career-platform
az vm auto-shutdown -g rg-career-platform -n vm-career-platform --time 0200
```

## How the migration preserved the data

The plan was written first:
[`2026-10-08-railway-postgres-migration.md`](docs/superpowers/plans/2026-10-08-railway-postgres-migration.md),
committed on 2026-10-08, five days before the domain moved on 2026-10-13. The
full record, written afterward on 2026-10-26, is
[`docs/evidence/railway-migration.md`](docs/evidence/railway-migration.md).

- **The data didn't travel through Git.** I took a consistent `.backup`
  snapshot of the VM's SQLite database. `python -m app.content_copy` copied it
  once into an empty Postgres and reset the id sequences. Deploys never seed,
  and a test fails if a migration ever inserts content.
- **It's the real data, not the seed.** The seed writes 1 profile row. The VM
  had 19 rows, including the project categories and `site_meta` I added on
  2026-10-08, which no seed or migration writes.
- **It was checked record by record.** On 2026-10-26, all 19 VM rows were
  identical in Postgres, column for column. The rendered pages matched too,
  apart from the project added in Postgres after the move.
- **The rollback carries newer data back.** It copies Postgres into a fresh
  SQLite file before DNS would point back at the VM. That copy was tested on
  2026-10-26.

**Responsibilities that moved to Railway:**
- the operating system;
- the web entry point (nginx's job);
- TLS certificates (Certbot's job);
- keeping the process running (systemd's job);
- running the database server.

**Still mine:**
- the code and its packages;
- the configuration and secrets;
- the data and its backups (the Trial has no built-in backups);
- migrations;
- DNS;
- costs.

The full who-manages-what table is in section 7 of the migration record.

## Decisions

| Decision | Alternatives considered | Why | Where it's written |
|---|---|---|---|
| **Move from the Azure VM to Railway + PostgreSQL** | Stay on the VM; Railway with SQLite on a volume | The course moves to a platform-as-a-service. Railway deploys on every push to `main`, terminates TLS and runs Postgres for me, so I stop patching an OS and renewing certificates. A SQLite file in a Railway container would be wiped on every deploy, so Postgres it is. The cost: a trial that ends, one custom domain, and less control | [Migration plan](docs/superpowers/plans/2026-10-08-railway-postgres-migration.md) (written before, 2026-10-08), [database choice](docs/database-choice.md) |
| **Managed email (Zoho Mail) instead of self-hosted** | A mail server (Postfix and Dovecot) on the VM; Namecheap's email forwarding | Running my own mail server means more open ports, spam filtering, patching, and a new IP address that big providers don't trust. Azure also restricts outbound port 25 on most subscriptions. Namecheap forwarding can receive but can't send as my domain with DKIM. Zoho's free plan gives a real mailbox with MX, SPF and DKIM values to publish, and mail keeps working whichever host runs the website | Written afterward, 2026-10-26 (this README). Results: [`ex06.md`](docs/evidence/ex06.md) |
| **`www` redirected by Cloudflare** | A second custom domain on Railway; a paid Railway plan | The Trial allows one custom domain per service. A proxied placeholder `www` record plus a Cloudflare redirect rule keeps one address for free, with a valid certificate | [`domain-https.md`](docs/evidence/domain-https.md) |
| **Opt-in analytics** | Load GA on every page | Nothing goes to Google unless the visitor accepts, so the privacy page is true. The cost: the numbers undercount visitors | [`analytics.md`](docs/evidence/analytics.md) |

## Investigated failures

Each one records the symptom, what I checked, the diagnosis, the repair, and
the repeated check.

| Failure | Kind | Symptom | Checks | Diagnosis and repair | Repeated check |
|---|---|---|---|---|---|
| **Data check said the VM's database differed from my laptop's** ([`ex03.md`](docs/evidence/ex03.md), section 3) | Application / database, real, during the Azure move | The `sqlite3 .dump` hashes from the two machines didn't match | Row counts per table; `/proc/<pid>/fd` showed which file the app had open; the profile row and homepage | The machines run different `sqlite3` versions (3.54 and 3.45), which format `.dump` output differently. The data was fine. I switched to hashing the database file itself | `sha256sum` of the file matched on both sides (`2a19d5ba…72b52`), checked again with the app running |
| **A merge never deployed** (PR #22, 2026-10-21) | Deployment, real, on Railway | The site still ran the PR #21 build hours after PR #22 was merged | `railway deployment list -s web`: the newest deployment was `e5d4c90` (PR #21), with no failed or skipped attempt for `f72dc41` | Railway never started a deploy for that push. I didn't confirm why. Repaired by "Deploy Latest Commit" in the dashboard. I then added `"commit"` to `/health` (PR #28), so the live commit shows at a glance | Deployment `f72dc41`: SUCCESS on 2026-10-26, `/health` healthy. Every merge since (PRs #23–#31) deployed by itself, and `/health` showed each merge commit |
| **TLS hostname mismatch** ([`ex05.md`](docs/evidence/ex05.md)) | DNS / TLS, **a deliberate lab failure** with simulated output from the exercise | `curl: (60) SSL certificate problem: certificate subject name does not match target host name` | `dig` (DNS resolved fine), `curl -Iv` (certificate subject `CN=old-vm.lab.example`) | The server presented a certificate for another host name. Repair: install a certificate for `site.lab.example` | The supplied follow-up showed `SSL certificate verify ok` and `HTTP/2 200` |
| **Old MX records still showing after the switch** (Exercise 06, 2026-10-15) | DNS, real | After I deleted Namecheap's MX records, Google's `8.8.8.8` still returned `eforward1` | Asked Cloudflare's name servers (`liz`, `sevki`) directly: they were already clean | A cached answer at the resolver. It expired with the 300-second TTL. Along the way, one "NXDOMAIN" turned out to be my command: zsh didn't split `$q` into two words for `dig` | `dig @8.8.8.8 MX gavinclarke.me` returned only Zoho's three records. Rechecked on 2026-10-26: still the same on `8.8.8.8` and Cloudflare |

[Exercise 04](docs/evidence/ex04.md) is my own explanation of how HTTPS
secured the site on the VM.

## Remaining limitations

- **The Azure subscription is disabled (found 2026-10-26).** The VM can't
  start, so I couldn't run a timed reboot test, and the rollback to the VM
  can't run until the subscription is re-enabled. The VM's resources may
  eventually be deleted ([`azure-vm.md`](docs/evidence/azure-vm.md)).
- **No email test before MX.** I didn't send a message before Zoho's MX
  records existed. The domain always had Namecheap's forwarding MX records
  before that ([`ex06.md`](docs/evidence/ex06.md)).
- **The address isn't resume-style.** It's `career-platform@` rather than
  `gavin@`. An alias would fix that without DNS changes.
- **DMARC is `p=none`.** Receivers report failing mail but don't block it.
- **No built-in Postgres backups on the Trial.** Backups are manual copies to
  SQLite (see [Rollback](#rollback)).
- **During a database outage, the profile comes from `app/fallback_data.py`.**
  That includes the home page's "What I've done so far" list. It's only as
  current as that file.
- **Not tested:** Railway's dashboard **Rollback** button. The README's rollback
  uses `git revert` as the main path.
- **No CI:** tests run locally before each PR, not automatically on GitHub.
- **Config-as-Code deprecation:** Railway retires `railway.json` on
  2026-12-01. The site will be on AWS by then.

## Costs and cleanup

The details and amounts are in [`docs/costs.md`](docs/costs.md).

| Service | Plan and cost | Ends or renews | Cleanup plan |
|---|---|---|---|
| Railway | Trial, $5 credit. **$3.91 left and 13 days on 2026-10-26** | **2026-11-07** | Move to AWS after the midterm, before 2026-11-07. Then take a final Postgres backup, delete the Railway project, and remove the SSH key `gavin-laptop` |
| Azure | Free trial, $5.46 used to 2026-10-20. **Subscription disabled (read-only) on 2026-10-26** | — | Keep the VM until the instructor says otherwise (see limitations). Then delete `rg-career-platform` |
| Domain `gavinclarke.me` | $0 for the first year (GitHub Student Pack), Namecheap | Expires 2027-10-08 | Renew at Namecheap's regular price, or let it lapse after the course |
| Zoho Mail | Free plan | — | Keep. Add a `gavin@` alias |
| Cloudflare | Free plan | — | Keep. Point `@` at AWS during that move |
| Google Analytics | Free | — | Keep |

## Reflection

*Draft for me to rewrite in my own words before submitting.*

- **What I understand better:**
  - A request passes through several layers: DNS, the TLS endpoint, a proxy,
    the app server and the database. When something breaks, checking each
    layer on its own (with `dig`, `curl -v` and the logs) finds the cause
    faster than guessing.
  - Moving to a platform didn't remove my responsibilities. It changed them:
    the OS and certificates went to Railway, but data, backups, migrations,
    secrets and costs are still mine.
  - Code and data roll back separately.
- **What I'd change:**
  - Write the before-MX test and the timed reboot test into the plan, and run
    them when they're due, not afterward.
  - Pick a resume-style email address from the start.
  - Add CI that runs the tests on every PR.
  - Check sooner that each deploy actually happened. That's what `"commit"`
    in `/health` now does.

## Project history

- **Spec:** [`resume-career-platform-spec.md`](docs/superpowers/specs/resume-career-platform-spec.md),
  committed on 2026-09-22.
- **Plans.** The date in each file name is when the plan was started. The
  first commit shows when it entered Git:

  | Plan | First committed |
  |---|---|
  | [Build](docs/superpowers/plans/2026-09-17-resume-career-platform.md) | 2026-09-22, with the spec, after the first build commit (2026-09-17) |
  | [Azure VM move](docs/superpowers/plans/2026-09-24-azure-vm-migration.md) | 2026-10-07 |
  | [Operating the VM](docs/superpowers/plans/2026-10-01-operate-the-vm.md) | 2026-10-08 |
  | [Railway move](docs/superpowers/plans/2026-10-08-railway-postgres-migration.md) | 2026-10-08, five days before the cutover |

  The plans also hold the results recorded while each step ran.
- **Evidence:** indexed by requirement in
  [`docs/project-1-submission.md`](docs/project-1-submission.md).
- **Commits:** since 2026-10-13, every change to `main` has come through a
  pull request (`git log --first-parent --no-merges main` lists no direct
  commits).
