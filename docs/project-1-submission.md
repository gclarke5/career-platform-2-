# Project 1 submission

The system is explained in the [README](../README.md). This index links the
evidence for each requirement. Pages marked "written afterward" were written
on 2026-10-26 from records made during the work and from checks rerun that
day; each page says which is which.

## 1. Profile and projects from a database

- [Why SQLite first, then PostgreSQL](database-choice.md) (written afterward)
- README: [Fallback](../README.md#fallback). With the database down, pages
  return 503 with "Projects temporarily unavailable", and recover without a
  restart. Tests are in `tests/test_database_content.py` (PR #22)
- The "This Website (In Progress)" project is live at
  <https://gavinclarke.me/projects/this-website>

## 2. Deploy and operate on Azure

- [Running the site on the Azure VM](evidence/azure-vm.md) (written afterward):
  nginx, uvicorn with 2 workers under systemd, SQLite, SSH and network rules,
  and restart checks
- [Exercise 03: Build it, then move it](evidence/ex03.md): the VM, the site
  served from it, and what went wrong during the move
- [Operate-the-VM plan and results](superpowers/plans/2026-10-01-operate-the-vm.md)
- [Azure VM migration plan](superpowers/plans/2026-09-24-azure-vm-migration.md)

## 3. Domain and HTTPS

- [Domain and HTTPS](evidence/domain-https.md) (checks run on 2026-10-26):
  - Cloudflare records;
  - root and `www` checks;
  - certificates and renewal;
  - the DNS move from the VM to Railway.
- [Exercise 04: How this site is secured](evidence/ex04.md): my own HTTPS
  explanation, written on the Azure VM
- [Exercise 05: Investigate a DNS or TLS failure](evidence/ex05.md): a
  deliberate lab failure, with simulated output

## 4. Migrate to Railway and PostgreSQL

- [Railway migration plan](superpowers/plans/2026-10-08-railway-postgres-migration.md):
  written before the move (committed 2026-10-08, cutover 2026-10-13). The
  project spec is [here](superpowers/specs/resume-career-platform-spec.md)
- [Moving to Railway and PostgreSQL](evidence/railway-migration.md) (written
  afterward):
  - what Git moved, and what needed another method;
  - the Postgres changes;
  - the record and page comparison;
  - the cutover;
  - the rollback;
  - who manages what.

## 5. Publish a reviewed change through Railway

- [Publishing a reviewed change through Railway](evidence/railway-deploy.md):
  PR #28, from local checks to commit, Railway deployment and the live
  `/health`
- README: [Rollback](../README.md#rollback), for code, schema and content

## 6. Email at the domain

- [Exercise 06: Custom-domain email with Zoho Mail](evidence/ex06.md): the
  results sheet, with:
  - the before-MX line;
  - the mail records;
  - the SPF, DKIM and DMARC results.
- [Zoho header check](evidence/zoho-header-check.md): the received headers of
  a Zoho message
- [DNS before Zoho](evidence/dns-before-zoho.md): the zone on 2026-10-13,
  before any mail changes

## 7. Google Analytics

- [Measuring activity with Google Analytics](evidence/analytics.md):
  - the setup;
  - how browser activity reaches Google;
  - the Realtime page view and outbound click;
  - the network check;
  - why the events matter.

## 8. Engineering record

- [README](../README.md):
  - what the site does, and its setup;
  - the architecture diagrams;
  - rollback;
  - the migration;
  - decisions;
  - investigated failures and limitations;
  - costs and cleanup;
  - a reflection.
- [Costs and the Railway trial end date](costs.md): the Railway trial ends
  2026-11-07
- [Project spec](superpowers/specs/resume-career-platform-spec.md) and
  [build plan](superpowers/plans/2026-09-17-resume-career-platform.md)
