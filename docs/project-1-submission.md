# Project 1 submission

| | |
|---|---|
| Repository | <https://github.com/gclarke5/career-platform-2-> |
| Live site | <https://gavinclarke.me> |
| Final commit | The merge commit on `main` that added this section, submitted in Brightspace. The only change after `2a16cf2` (the commit checked below) is this file. `curl -s https://gavinclarke.me/health` returns the live commit as `"commit"` |

The system is explained in the [README](../README.md). Pages marked "written
afterward" were written on 2026-10-26 from records made during the work, plus
checks rerun that day. Each page dates its observations.

## Final check of the live system (2026-10-26, 13:29 PDT)

Run against commit `2a16cf2`:

```text
$ curl -s https://gavinclarke.me/health
{"status":"ok","database":"healthy","fallback":false,"commit":"2a16cf2"}
$ curl -s -o /dev/null -w '%{http_code}' https://gavinclarke.me<path>
200 /    200 /resume    200 /projects    200 /projects/this-website    200 /contact    200 /privacy
$ curl -s -o /dev/null -w '%{http_code} -> %{redirect_url}' <url>
301 -> https://gavinclarke.me/   http://gavinclarke.me/
301 -> https://gavinclarke.me/   http://www.gavinclarke.me/
301 -> https://gavinclarke.me/   https://www.gavinclarke.me/
$ echo | openssl s_client -connect gavinclarke.me:443 -servername gavinclarke.me 2>/dev/null | openssl x509 -noout -subject -enddate
subject=CN=gavinclarke.me
notAfter=Jan 11 18:37:00 2027 GMT
$ dig +short MX gavinclarke.me
10 mx.zoho.com.
20 mx2.zoho.com.
50 mx3.zoho.com.
$ curl -s https://gavinclarke.me/ | grep -o 'data-ga-id="[^"]*"'
data-ga-id="G-FVPBZ69VK0"
```

The site stays up on Railway's trial until at least 2026-11-07 ([costs](costs.md)).

## README, spec and plans

- [README](../README.md)
- [Original application spec](superpowers/specs/resume-career-platform-spec.md)
- Plans, with their first-commit dates in the README's
  [project history](../README.md#project-history):
  - [Build](superpowers/plans/2026-09-17-resume-career-platform.md)
  - [Azure VM move](superpowers/plans/2026-09-24-azure-vm-migration.md)
  - [Operating the VM](superpowers/plans/2026-10-01-operate-the-vm.md)
  - [Railway + PostgreSQL move](superpowers/plans/2026-10-08-railway-postgres-migration.md)

## Profile and projects from the database

- [Why SQLite first, then PostgreSQL](database-choice.md) (written afterward)
- README, [Fallback](../README.md#fallback):
  - with the database down, the profile still shows;
  - project pages return 503 with "Projects temporarily unavailable";
  - they recover without a restart;
  - an empty table says "No projects yet".

  The tests are in `tests/test_database_content.py` (PR #22).
- "This Website (In Progress)": <https://gavinclarke.me/projects/this-website>
  (200 on 2026-10-26)

## Architecture diagrams

All in the README's [Architecture](../README.md#architecture) section. The
email and analytics paths are drawn in:

- [Railway (now)](../README.md#now-railway-since-2026-10-13): includes the GA4
  path from the browser
- [Azure VM (before)](../README.md#before-azure-vm-2026-10-08-to-2026-10-13):
  includes the GA4 path
- [Email (Zoho Mail)](../README.md#email-zoho-mail): incoming, outgoing, and the
  SPF/DKIM/DMARC checks

## Migration: plan, data comparison, cutover and rollback

- **Plan:** [Railway + PostgreSQL migration plan](superpowers/plans/2026-10-08-railway-postgres-migration.md),
  committed 2026-10-08, before the 2026-10-13 cutover
- **Record:** [Moving to Railway and PostgreSQL](evidence/railway-migration.md)
  (written afterward):
  - what Git moved and what didn't (section 2);
  - Postgres compatibility (section 3);
  - the source/target record comparison and rendered-page comparison,
    rerun 2026-10-26 (section 4);
  - testing before the domain moved (section 5);
  - the cutover timeline, post-cutover checks, and a rollback that carries
    post-cutover data, with its copy tested 2026-10-26 (section 6);
  - who manages what (section 7).
- **Summary:** README, [How the migration preserved the data](../README.md#how-the-migration-preserved-the-data)
- **Database choice:** [Why SQLite first, then PostgreSQL](database-choice.md)
- **Rollback for code, schema and content:** README, [Rollback](../README.md#rollback)

## Azure HTTP and restart evidence; final DNS and HTTPS

- [Running the site on the Azure VM](evidence/azure-vm.md) (written afterward):
  - SSH, addresses and network rules;
  - HTTP checks through nginx (2026-10-08);
  - crash and restart tests (2026-10-08);
  - the cold start from deallocated (2026-10-20).
- [Exercise 03](evidence/ex03.md): the site served from the VM, with `curl`
  output (2026-10-20), and the failure during the move
- [Exercise 04](evidence/ex04.md): my HTTPS explanation, written on the VM
- [Domain and HTTPS](evidence/domain-https.md) (checks run 2026-10-26):
  - the DNS records;
  - root and `www` over HTTP and HTTPS;
  - both certificates and their renewal;
  - the move from the VM's A record to Railway.

## A reviewed change through Railway

- [Publishing a reviewed change through Railway](evidence/railway-deploy.md):
  - **The change:** [PR #28](https://github.com/gclarke5/career-platform-2-/pull/28),
    verified locally before pushing;
  - **The commit:** feature commit `2069c80`, merge commit `bbb47d8`;
  - **The deployment:** Railway deployment `49d3c114-d85a-4bfe-86c8-92494d81e31b`;
  - **The live result:** `https://gavinclarke.me/health` returned
    `"commit":"bbb47d8"` (2026-10-26).

## Zoho email

- [Exercise 06 results sheet](evidence/ex06.md):
  - the before-MX line;
  - receive (2026-10-15), reply (2026-10-20) and send (2026-10-15) tests;
  - the sender shown to the outside mailbox;
  - a dated Zoho Inbox screenshot;
  - the MX, SPF, DKIM and DMARC records, explained and checked with `dig`
    on 2026-10-26;
  - the authentication results.
- [Zoho header check](evidence/zoho-header-check.md): the received headers of
  "Test 02: New Outbound" (2026-10-15), with SPF, DKIM and DMARC passing for
  `gavinclarke.me`
- [DNS before Zoho](evidence/dns-before-zoho.md): the zone on 2026-10-13,
  before any mail changes

## GA4

- [Measuring activity with Google Analytics](evidence/analytics.md):
  - the setup;
  - how browser activity reaches Google;
  - Realtime `page_view` and outbound `click` screenshots (2026-10-20);
  - the network check with consent and decline (2026-10-26);
  - why the events are useful.

## Failures, decisions, reflection, costs and limitations

- README sections:
  - [Investigated failures](../README.md#investigated-failures): the ex03 data
    check (app/DB), the PR #22 deploy, ex05 (a deliberate DNS/TLS lab) and the
    stale MX records (DNS);
  - [Decisions](../README.md#decisions);
  - [Reflection](../README.md#reflection);
  - [Costs and cleanup](../README.md#costs-and-cleanup);
  - [Remaining limitations](../README.md#remaining-limitations).
- Records:
  - [Exercise 03](evidence/ex03.md), section 3;
  - [Exercise 05](evidence/ex05.md) (a deliberate lab failure, with
    simulated output);
  - [Costs and the Railway trial end date](costs.md).

## Unverified or not done

| Item | Status | Where |
|---|---|---|
| Timed VM reboot test | Not done. The Azure subscription is disabled (2026-10-26), so the VM can't start. The crash tests and the 2026-10-20 cold start are the restart evidence | [`azure-vm.md`](evidence/azure-vm.md), section 4 |
| Certbot renewal on the VM | Unverified. No `--dry-run` or timer output was recorded, and it can't run now | [`domain-https.md`](evidence/domain-https.md), section 5 |
| Rollback to the VM | Can't run until the Azure subscription is re-enabled. The Postgres-to-SQLite copy step was tested 2026-10-26 | [`railway-migration.md`](evidence/railway-migration.md), section 6 |
| Email before MX | Not done. The domain had Namecheap forwarding MX records until Zoho's | [`ex06.md`](evidence/ex06.md), section 1 |
| The reply as seen in iCloud | Not saved. Zoho's Sent folder shows it was sent from `career-platform@gavinclarke.me` | [`ex06.md`](evidence/ex06.md), section 1 |
| GA4 Outbound clicks setting | Not viewed directly. It's inferred from the `click` events with `outbound=true` | [`analytics.md`](evidence/analytics.md), section 1 |
| Railway dashboard **Rollback** button | Not tested. The README uses `git revert` as the main path | README, [Rollback](../README.md#rollback) |
| Railway Postgres backups | Not available on the Trial. A manual backup was taken 2026-10-26 | README, [Rollback](../README.md#rollback) |
