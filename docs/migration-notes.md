# Migration notes: Railway to AWS EC2 + RDS (2026-11-10)

The plan, written first, is
[`superpowers/plans/2026-11-10-aws-ec2-rds-migration.md`](superpowers/plans/2026-11-10-aws-ec2-rds-migration.md)
(commit `c2e1eed`, 10:32 PST). It follows the course guide `aws-migration.md`.
Times below are Pacific.

## Starting point

- Railway's trial ended on **2026-11-07**. From then on `gavinclarke.me`
  returned Railway's "Application not found" 404; `web` was Failed and
  Postgres Offline. There was no live source to copy from and no fallback.
- The data source was the last backup,
  `railway-pg-2026-11-03-132243.dump` (`pg_dump -Fc --no-owner --no-acl`,
  PG 18.6, 24 121 bytes, SHA-256 `7ce0c7d7…0718139817`). On 2026-11-03 it was
  restored into a throwaway local PostgreSQL 18 as a non-superuser: all 10
  tables matched Railway's row counts and md5 content fingerprints, and the
  app served every page from it. No content was edited after 2026-11-03.
- Backups are kept outside the repo, in `../railway-move/`.

## What was built

| Resource | Name / ID | Key settings |
|---|---|---|
| Security group | `career-platform-web` `sg-03d240f3bf0a340db` | 22 from `99.7.122.53/32` (home), 80 and 443 from anywhere |
| Security group | `career-platform-db` `sg-0e3c2b31ca95adbd1` | 5432 only from `career-platform-web` |
| DB subnet group | `career-platform-db-subnets` | default VPC, all 6 us-east-1 subnets |
| RDS | `career-platform-db` | PostgreSQL 18.6, db.t4g.micro, gp3 20 GiB, no autoscaling, Single-AZ, **not public**, encrypted (`aws/rds`), backups 1 day, deletion protection, Enhanced Monitoring and Performance Insights off, maintenance Mon 11:00 UTC |
| Key pair | `isba4775-aws` | ed25519, **imported**: the private key (with a passphrase) never left the laptop |
| EC2 | `career-platform-web` `i-0bc13a8b3e864e62e` | Ubuntu 26.04 (`ami-0547ecbf0e9b4aeb5`), t3.micro, IMDSv2 required, Standard credits, 20 GiB gp3 encrypted, us-east-1c |
| Elastic IP | `100.56.44.71` `eipalloc-0e97da408a2ce7d66` | attached to the instance |

All are tagged `Project=career-platform`. Everything was created as the IAM
user `isba-student` under the course's `ISBA4775EC2Migration` policy, never as
root.

## Timeline

| Time | Step | Result |
|---|---|---|
| 10:32 | Plan committed on branch `aws-migration` | `c2e1eed` |
| ~11:20 | DB password generated into `~/.config/career-platform/aws-db-password` (600, 32 alphanumeric, never displayed); CLI signed in as `isba-student` | `sts get-caller-identity` → `user/isba-student` |
| ~11:30 | Security groups, subnet group, RDS created | Read back: `PubliclyAccessible false`, `StorageEncrypted true`, `MultiAZ false`, only `career-platform-db` SG, `DeletionProtection true` |
| 11:46 | Key imported, EC2 launched, Elastic IP attached | Fingerprints matched; IMDSv2 `required`, credits `standard`, volume encrypted |
| ~11:48 | SSH host key checked | `SHA256:x25uS6Ii…VSNK4` from `get-console-output` matched `ssh-keyscan` before the first login |
| 11:52 | Code fixes (`90c268b`) | 74 tests pass |
| ~11:55 | Server packages: nginx 1.28.3, certbot 4.0.0, `postgresql-client-18` 18.6, uv 0.13.7 (Python 3.12.16), unattended-upgrades enabled | — |
| ~11:57 | Restore into RDS, then `alembic upgrade head` | see "Data checks" |
| ~11:59 | systemd + nginx installed, `deploy.sh` run | `/health` ok at `90c268b` |
| ~12:00 | Reboot test | back in under a minute, `career-platform` and `nginx` active, `/health` healthy |
| ~12:01 | `aws.gavinclarke.me` A record (DNS only) and certificate | 9 pages 200 over HTTPS, `noindex` header present |
| 12:03 | Privacy page wording (`296d035`) deployed with `deploy.sh` | live |
| 12:04 | DNS backed up, `@` changed from CNAME (Railway) to A `100.56.44.71` | resolves on 1.1.1.1 and 8.8.8.8 |
| ~12:05 | Certificate expanded to `gavinclarke.me`; `certbot renew --dry-run` | success |
| 12:05 | One export to the laptop for Google Drive | 10 tables, same counts |

## Data checks

- The dump arrived on the server with the same SHA-256 (`7ce0c7d7…`).
- `pg_restore --no-owner --no-acl --exit-on-error` into the empty
  `career_platform` database (0.2 s). With `--exit-on-error`, any existing
  object would have stopped it.
- Row counts: `alembic_version` 1, `certifications` 0, `education` 1,
  `experiences` 3, `links` 0, `profiles` 1, `projects` 4, `site_meta` 2,
  `skills` 7, `volunteer_work` 2. Same as 2026-11-03.
- **Row by row:** every data row in RDS (`pg_dump --data-only`) was compared
  with every row in the backup file (`pg_restore --data-only`), sorted per
  table: **21 = 21, identical**. All **9 sequence values** identical.
- `alembic upgrade head` made no change; `alembic current` →
  `d4a8f1c2e7b9 (head)`.
- Project slugs: `mlb-predictive-model`, `operations-forecasting-intel`,
  `portfolio-performance-asset-allocation`, `this-website`.
- The dump was deleted from the server with `shred -u`.

## Live checks after the cutover

| Check | Result |
|---|---|
| `/`, `/resume`, `/projects`, `/contact`, `/privacy`, all 4 project pages | 200 on `https://gavinclarke.me` |
| `/admin`, `/admin/profile` | 404 (closed in the app and in nginx) |
| `/health` | `{"status":"ok","database":"healthy","fallback":false,"commit":"296d035"}` |
| `http://gavinclarke.me/` | 301 to `https://gavinclarke.me/` |
| `https://www.gavinclarke.me/resume` | 301 to `https://gavinclarke.me/resume` (Cloudflare) |
| Certificate | Let's Encrypt, SANs `gavinclarke.me` and `aws.gavinclarke.me`, expires 2027-02-08, renewal dry run passed |
| `X-Robots-Tag` | none on `gavinclarke.me`; `noindex, nofollow` on `aws.gavinclarke.me` |
| Bare IP `100.56.44.71` on 80 and 443 | no response (444 / handshake rejected) |
| Port 8000 and the RDS endpoint from the laptop | unreachable |
| DNS | only `@` changed (CNAME → A); all 3 MX and 5 TXT records (SPF, DKIM, DMARC, Zoho verification, Railway verification) identical to the backup |

## Code changes

- `ENVIRONMENT` defaults to `production`. The old `/admin` guard relied on
  Railway setting `RAILWAY_ENVIRONMENT`, so on any other host a missing
  `ENVIRONMENT` would have exposed the unauthenticated `/admin`.
- Outside development the app refuses to start on SQLite. Before, a missing
  `DATABASE_URL` silently used an empty SQLite file and `/health` still said
  healthy.
- `/health` reads `GIT_COMMIT_SHA` (written by `deploy.sh`), falling back to
  `RAILWAY_GIT_COMMIT_SHA`.
- `deploy/`: `deploy.sh`, the systemd unit (uvicorn on `127.0.0.1:8000`,
  trusting forwarded headers only from `127.0.0.1`), the nginx site.
- The privacy page says the site runs on AWS and that server logs are kept
  about two weeks (nginx's logrotate: daily, 14 files).
- `railway.json` and the tests that read it were removed; the proxy test now
  starts uvicorn with the systemd unit's own command line.

## Differences from the plan

- **Backups are 1 day, not 7.** `CreateDBInstance` with 7 days failed with
  `FreeTierRestrictionError: The specified backup retention period exceeds the
  maximum available to free tier customers.` Upgrading the account plan
  needs root and ends the Free plan's protections, so retention is 1 day. It
  still meets "losing up to a day is acceptable"; exports outside AWS are the
  longer-term copies.
- **The AWS resources were created with the CLI, not by clicking.** To meet
  the deadline, the console screens were explained step by step while the
  same settings were applied with `aws` commands, then read back.
- **The first `aws login` used root by mistake.** It was signed out with
  `aws logout` before any AWS call was made, and the account was checked: no
  resources existed yet.
- **Content fingerprints:** the 2026-11-03 fingerprint files were in a
  temporary folder that had been cleared, so the check compared RDS with the
  backup file row by row instead (a stricter check).
- **A newer Ubuntu image** than the one noted on 2026-11-04, from Canonical's
  SSM parameter on the day.
- **Certbot:** the first `renew --dry-run` sat in certbot's random delay;
  stopping it with `pkill -f` also matched the SSH session's own command line
  and ended it (exit 255). Nothing was changed by that; the expansion and the
  dry run were run again and passed.
- Ahead of schedule: live at about 12:05 against a 13:45 deadline.

## Done after the cutover (2026-11-10)

- **Mail:** a send-and-reply test to my `gavinclarke.me` address worked.
- **Export outside AWS:** `aws-rds-career-platform-2026-11-10-120544.dump`
  (SHA-256 `2e7cd593…0b2c63`) is uploaded to my personal Google Drive.
- **Railway cleanup:**
  - The stale `_railway-verify` TXT record is deleted from Cloudflare.
  - The SSH key `gavin-laptop` is removed from Railway (`railway ssh keys
    list` shows none). The key file stays on the laptop for the Azure VM.
  - The project `renewed-strength` is deleted. Railway shows it as deleted
    with a grace period ending 2026-11-12 20:20 UTC.
  - `gavinclarke.me` stayed on AWS and healthy throughout.

## Changes after the cutover

- **2026-11-10, hide the nginx version.** Testing showed the HTTP redirect
  block that Certbot added answered with `Server: nginx/1.28.3 (Ubuntu)`; the
  site's own `server_tokens off;` only covered its main block.
  - First attempt (failed): a `conf.d/hide-version.conf` with
    `server_tokens off;`. Ubuntu 26.04's `nginx.conf` already sets
    `server_tokens build;`, so `nginx -t` rejected the duplicate. A `| tail -1`
    hid that failure and the reload ran anyway; it failed too, and nginx kept
    serving the old config (no downtime, `/health` healthy throughout). The
    file was removed and `nginx -t` passed again.
  - Fix: backed up `nginx.conf` to `nginx.conf.bak-2026-11-10`, changed line
    22 to `server_tokens off;`, ran `nginx -t`, then reloaded.
  - Check: `Server: nginx` with no version on HTTP and HTTPS for both names;
    the 301 redirect and `/health` unchanged.
  - Not in the repo's files, so `deploy/nginx-career-platform.conf` now says
    to set it when rebuilding.

## Not verified

- An RDS point-in-time restore and a schema downgrade on the server have not
  been practised.
- The class policy's `DenyMakingDatabasePublic` rule probably doesn't apply
  to `ModifyDBInstance`, so it isn't a safety net.

## Cost

About **$26.82 a month** on the $100 Free-plan credits (details in
[`costs.md`](costs.md)), which last until about 2027-03-03. The plan is to
move to a ~$8–10/month setup by the end of February 2027.
