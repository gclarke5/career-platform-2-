# Moving to Railway and PostgreSQL

Written on 2026-10-26. The move happened between 2026-10-08 and 2026-10-13. The
record comparison, page comparison and rollback copy in sections 4 and 6 were
rerun on 2026-10-26.

## 1. The plan came first

| Document | What it is |
|---|---|
| [Migration plan](../superpowers/plans/2026-10-08-railway-postgres-migration.md) | Inventory of what the target needs, what breaks on Postgres, constraints, eight tasks with checks, results, cutover record and rollback |
| [Project spec](../superpowers/specs/resume-career-platform-spec.md) | The original requirements for the site, which the move had to keep |
| [Operate-the-VM plan](../superpowers/plans/2026-10-01-operate-the-vm.md) | The Azure setup being moved away from |

The plan was committed on 2026-10-08 at 15:16 PDT (`f4f6f86`). The domain moved
on 2026-10-13 at 12:30 PDT, so the plan existed five days before the working
deployment changed. There's no separate spec for the move: the plan's sections
"Where things stand", "What breaks today if you just point the app at Postgres"
and "Global Constraints" set out the requirements, and the plan says so.

## 2. What the target needed, and how each part got there

| Part | What Railway needed | How it moved |
|---|---|---|
| Code | The FastAPI app, templates and static files | **Git.** Railway builds `main` of `gclarke5/career-platform-2-` on every push |
| Runtime | Python 3.12 | **Git.** `.python-version`; Railpack (Railway's builder) detects Python and installs it |
| Packages | Everything in `uv.lock`, plus a Postgres driver (`psycopg[binary]`) | **Git.** Added the driver to `pyproject.toml`, `uv.lock` and `requirements.txt` |
| Schema | The 9 content tables at Alembic revision `d4a8f1c2e7b9` | **Git.** The migrations are in `migrations/versions/`; Railway's pre-deploy step runs `alembic upgrade head` before each deploy |
| Configuration | Start command, pre-deploy command, health check, restart policy, `ENVIRONMENT=production` | **Partly Git.** `railway.json` holds the values, but Railway didn't apply it to this service, so I also set them on the service and in the `RAILPACK_START_CMD` variable |
| Secrets | The database password | **Not Git.** `DATABASE_URL=${{Postgres.DATABASE_URL}}` is a reference that Railway resolves inside the project, so the password is never in Git, chat or command output |
| Current data | The live rows in the VM's SQLite file | **Not Git.** A consistent snapshot (`sqlite3 .backup`) from the VM, copied into Postgres once by `python -m app.content_copy` |
| Domain and TLS | DNS records and a certificate | **Not Git.** Cloudflare records changed by hand; Railway issued the certificate (see [Domain and HTTPS](domain-https.md)) |

Git moves anything that's the same on every copy of the site: code, packages,
schema and config files. It can't move things that exist only on the running
system or must stay secret: the data, the password, DNS and the certificate.

## 3. Making it work on PostgreSQL

The plan listed what would break if the app were simply pointed at Postgres.
Each one got a code change and a test (PR #5):

| Problem | Change |
|---|---|
| No Postgres driver | Added psycopg 3 |
| Railway's `postgresql://` URL makes SQLAlchemy look for the old psycopg2 driver | `normalize_database_url()` rewrites `postgres://` and `postgresql://` to `postgresql+psycopg://` |
| Alembic always migrated a hardcoded SQLite file, so Postgres would have stayed empty | `migrations/env.py` now uses the app's `DATABASE_URL` |
| `/admin` was only hidden by nginx on the VM, so it would have been public on Railway | The app doesn't mount `/admin` at all when `ENVIRONMENT=production` |
| No connect timeout, so a Postgres outage would hang pages | Postgres connections time out quickly and pre-ping, so pages fall back in seconds |
| Copying rows with their ids doesn't move Postgres's id counters, so the next new row would collide with id 1 | The copy script resets each table's sequence past the highest copied id |
| Postgres enforces `String(n)` lengths, which SQLite ignores | Checked before the copy: every value was well under its limit |

The whole test suite runs on both engines: 51 tests passed on SQLite and on a
local Postgres before the move (60 on each now). One test fails if any
migration ever inserts content, because every deploy runs the migrations.

## 4. The transferred data is the real data, not the seed

**Restoring the seed couldn't pass as the transfer.** `seed_database()` only
writes one profile row. Run on a fresh database on 2026-10-26, it produced
`profiles=1`, and 0 rows in every other table. The VM's database had 19 rows.

**Real changes I'd made to the data were carried over.** For the redesign on
2026-10-08 (`a417756`), the VM's database gained:

- a category on each project (`Finance`, `Operations & supply chain`,
  `Predictive modeling`);
- the `availability` line and the `proof_points` list in `site_meta`.

No seed or migration writes these values: the migration only adds an empty
`category` column, and a test proves migrations insert nothing. So their
presence in Postgres can only come from copying the VM's database.

**After the move,** I added a fourth project, "This Website (In Progress)", in
Postgres on 2026-10-26. It exists only in Postgres, which is why the rollback
in section 6 copies data back instead of reusing the VM's old file.

**Records compared** on 2026-10-26, every column of every row: the VM snapshot
taken at cutover (`vm-live.db`, 2026-10-13) against live Railway Postgres,
read through `railway connect`:

| Table | VM | Postgres | Identical |
|---|---|---|---|
| profiles | 1 | 1 | 1 |
| experiences | 3 | 3 | 3 |
| projects | 3 | 4 | 3, plus the new project (id 4) |
| skills | 7 | 7 | 7 |
| education | 1 | 1 | 1 |
| certifications | 0 | 0 | — |
| links | 0 | 0 | — |
| site_meta | 2 | 2 | 2 |
| volunteer_work | 2 | 2 | 2 |

All 19 VM rows are in Postgres unchanged.

**Rendered pages compared:** I ran the app locally on a copy of the VM snapshot
and compared each page's `<main>` with the live site:

| Page | Result |
|---|---|
| `/resume`, `/contact` | Identical |
| `/projects/operations-forecasting-intel`, `/projects/portfolio-performance-asset-allocation` | Identical |
| `/`, `/projects` | Identical except the new "This Website (In Progress)" entry |
| `/projects/mlb-predictive-model` | Identical except its "next project" link, which now points to the new project |

The same comparison at cutover, before the new project existed, found the
`<main>` of `/`, `/resume`, `/projects`, `/contact`, a project page and the
stylesheet identical to the VM's.

## 5. Deploy, secrets and tests before the domain moved

On 2026-10-13, before touching DNS (plan, Task 7):

1. **Set the variables:** `DATABASE_URL=${{Postgres.DATABASE_URL}}` and
   `ENVIRONMENT=production`, set with `--skip-deploys`. Variable checks printed
   names only, never values.
2. **First deploy:** connected the repo. The pre-deploy log showed all three
   Alembic upgrades to `d4a8f1c2e7b9`, and the deployment succeeded.
3. **Checked the empty state:** on `https://web-production-9277a.up.railway.app`
   with empty tables, the pages showed the fallback profile and `/admin`
   returned 404.
4. **Copied the data:** took a fresh `.backup` snapshot on the VM (integrity
   `ok`), copied it to the laptop, and ran the copy script into Postgres through
   a temporary TCP proxy. It printed the expected nine counts (19 rows).
5. **Tested on the Railway address:**
   - `/health` reported `"fallback": false`;
   - all pages returned 200, while `/projects/nope` and `/admin` returned 404;
   - redirects used `https://`;
   - the resume's `<main>` matched the live VM's.
6. **Closed the proxy:** deleted the temporary TCP proxy, so Postgres has no
   public address.

## 6. Cutover, checks and rollback

**Cutover** (2026-10-13, in Cloudflare):

| Time (PDT) | Change |
|---|---|
| 12:30:38 | `@`: A `20.114.0.108` (VM) replaced by CNAME `dwaascah.up.railway.app`, DNS only |
| 12:32:11 | TXT `_railway-verify` added |
| 12:58:34 | `www`: proxied placeholder record plus the redirect rule to `https://gavinclarke.me` |

The records were already on a 5-minute TTL, so the switch took effect quickly.
MX and SPF were left alone, and the VM kept running unchanged as the rollback.

**Post-cutover checks** (2026-10-13):

| Check | Result |
|---|---|
| DNS | The bare domain resolved to `69.46.46.23` (Railway) on Cloudflare, Google and Quad9 DNS |
| Server | `railway-hikari`, not nginx |
| Certificate | `CN=gavinclarke.me`, Let's Encrypt, valid to 2027-01-11 |
| `/health` | `"fallback": false` |
| `http://` | 301 to `https://gavinclarke.me/` |
| `/admin` | 404 |
| Pages | All 200, unknown project 404, no `http://` asset links |
| `www` | 301 to the same path on `https://gavinclarke.me`, in one hop |

Today's checks are in [Domain and HTTPS](domain-https.md).

**Rollback.** Visitors can't write to the site: `/admin` doesn't exist in
production. The only writes are my own content edits in Postgres, like the
project added on 2026-10-26. The VM's database stops at 2026-10-13, so
switching DNS back alone would lose those edits. The rollback copies Postgres's
current data back first:

1. **Freeze content:** make no edits in Postgres until the rollback is done.
2. **Copy Postgres into a fresh SQLite file** at the same schema, on the laptop:

   ```bash
   railway connect Postgres --tunnel-only --port 15432 &     # private tunnel, no public access
   DATABASE_URL=sqlite:///../railway-move/rollback.db uv run alembic upgrade head
   railway run --service Postgres -- sh -c 'TARGET_DATABASE_URL=sqlite:///../railway-move/rollback.db \
     .venv/bin/python -m app.content_copy "postgresql+psycopg://$PGUSER:$PGPASSWORD@127.0.0.1:15432/$PGDATABASE"'
   ```

   The password stays inside the single-quoted `sh -c`, so it's never printed.
   The copy refuses to write into a file that already has rows.
3. **Check the copy:** `sqlite3 -readonly ../railway-move/rollback.db "pragma
   integrity_check"` prints `ok`, and the row counts match what the copy printed.
4. **Start the VM and swap in the file:**
   - follow the README's rollback steps 1–2 (`az vm start`, check nginx answers);
   - `scp` the file to the VM;
   - stop `career-platform`;
   - keep the old `~/career-platform-data/career_platform.db` as a backup, and
     move the new file into its place;
   - start `career-platform` again.
5. **Check the VM:** `/health` shows `"fallback": false`, and every project in
   Postgres appears on `/projects` (with `curl --resolve` to the VM's IP).
6. **Move DNS back:** in Cloudflare, change `@` from the CNAME to an A record
   for `20.114.0.108`, DNS only. The `www` redirect can stay as it is.
7. **Check the domain:** check `https://gavinclarke.me` reaches nginx with a
   valid certificate. If Certbot's certificate has expired while the VM was
   off, run `sudo certbot renew`.

I tested steps 2 and 3 on 2026-10-26 against live Postgres, writing to a
scratch file. The copy printed all nine tables (20 rows), integrity was `ok`,
the schema was `d4a8f1c2e7b9`, and the new "this-website" project was included.
Nothing in Postgres was changed.

**Rollback can't run at the moment:** the Azure subscription is disabled (see
[the VM page](azure-vm.md)), so step 4 would fail until it's re-enabled.

## 7. Who manages what

| Layer | On the Azure VM | On Railway |
|---|---|---|
| Hardware and virtualisation | Azure | Railway |
| Operating system | **Me**: Ubuntu 24.04 updates, reboots, disk space | Railway: the container's base image and the hosts |
| Runtime | **Me**: installing Python and uv, upgrading them | Railway builds it (Railpack), but **I** pick the Python version (`.python-version`) and the packages (`uv.lock`) |
| Web entry point | **Me**: nginx config, the firewall (NSG) rules, systemd keeping the app up | Railway's edge proxy, health check and restarts. **I** set the start command, health check path and restart policy |
| TLS | **Me**: Certbot, and keeping its renewal working (renewal only runs while the VM is on) | Railway issues and renews the certificate, as long as **my** DNS keeps pointing at it |
| Application code | **Me** | **Me** |
| Configuration | **Me**: `.env` on the VM | **Me**: Railway variables and service settings, and keeping `railway.json` matched to them |
| Database software | **Me**: the `sqlite3` package on the OS | Railway runs PostgreSQL (18.6 today), but **I** decide on major-version upgrades |
| Data | **Me**: backups, the file's permissions and disk | **Me**: the content, edits, backups and restore tests. Railway stores it on its volume |
| DNS | **Me**, at Cloudflare | **Me**, at Cloudflare |

**What's still my job on Railway:**

- **Keep it paid for.** The trial ends on 2026-11-07, and then the site stops
  unless it's on a paid plan or moved (the AWS move is next). See
  [costs](../costs.md).
- **Keep packages up to date** in `uv.lock` for security fixes. Railway
  rebuilds with whatever versions I pin.
- **Back up the data.** Turn on, and test restoring from, Railway's Postgres
  backups (Postgres → Backups). Railway doesn't restore anything for me
  automatically.
- **Write and test migrations.** A broken migration stops the deploy.
- **Look after the secrets and access:**
  - keep the database private (Public access off);
  - remove the SSH key `gavin-laptop` if the laptop is lost.
- **Watch the site:**
  - check `/health` and the deploy logs;
  - check that deploys actually start, since one merge (PR #22) didn't deploy
    until I clicked "Deploy latest commit".
- **Keep up with Railway's changes.** Railway is retiring `railway.json`
  ("Config as Code") on 2026-12-01, and the TCP proxy option has already
  disappeared from the dashboard.
- **Keep the domain:**
  - renew `gavinclarke.me` before 2027-10-08;
  - keep the DNS records correct.
- **Keep `app/fallback_data.py` in step** with the profile in Postgres, so
  an outage still shows the right details.
