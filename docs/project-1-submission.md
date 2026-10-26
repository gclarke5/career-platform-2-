# Project 1 submission

## Evidence

- [Exercise 03: Build it, then move it](evidence/ex03.md): the Azure VM, the site served from it, and what went wrong during the move.
- [Running the site on the Azure VM](evidence/azure-vm.md): nginx, uvicorn with 2 workers under systemd, SQLite, SSH and network rules, and restart checks.
- [Domain and HTTPS](evidence/domain-https.md): Cloudflare DNS records, root and www checks, certificates and renewal, and the move from the VM to Railway.
- [Moving to Railway and PostgreSQL](evidence/railway-migration.md): what moved by Git and what didn't, Postgres changes, record and page comparison, cutover, rollback, and who manages what.
- [Railway migration plan](superpowers/plans/2026-10-08-railway-postgres-migration.md) and [project spec](superpowers/specs/resume-career-platform-spec.md): written before the move.
- [Publishing a reviewed change through Railway](evidence/railway-deploy.md): PR #28 from local checks to commit, Railway deployment and the live `/health`; rollback is in the [README](../README.md#rollback).
- [Exercise 04: How this site is secured](evidence/ex04.md): checking the HTTPS redirect and certificate (written on the Azure VM).
- [Exercise 06: Custom-domain email with Zoho Mail](evidence/ex06.md): email tests, SPF/DKIM/DMARC results, and website analytics.
- [Zoho header check](evidence/zoho-header-check.md): the received headers of a Zoho message, with SPF, DKIM and DMARC passing for `gavinclarke.me`.
- [Costs and Railway trial end date](costs.md): Railway trial ends 2026-11-07; Azure costs to date.
- [Why SQLite first, then PostgreSQL](database-choice.md): the database engine choice for each host.
