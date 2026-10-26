# Costs

Recorded on 2026-10-20.

## Railway (current host)

| Item | Value |
|---|---|
| Plan | Trial |
| Trial started | 2026-10-08 |
| **Trial ends** | **2026-11-07** (18 days left on 2026-10-20) |
| Credit used / left | $0.63 / $4.37 of $5.00 |
| Checked again 2026-10-26 | $3.91 left, 13 days left (Railway dashboard banner) |
| Average daily spend | about $0.05 (`web` and `Postgres` together) |

The trial ends after 30 days or $5 of usage, whichever comes first. At about
$0.05 a day the credit would last into January, so the 30-day limit is the one
that applies: the trial ends on **2026-11-07**.

The Free plan allows no custom domain, so the site has to be on AWS before
2026-11-07 or `gavinclarke.me` stops reaching it.

## Azure (previous host)

`rg-career-platform`, actual cost from 2026-09-01 to 2026-10-20, from Azure
Cost Management:

| Category | Cost (USD) |
|---|---|
| Virtual Network (static public IP) | $3.10 |
| Storage (OS disk) | $2.05 |
| Virtual Machines (compute) | $0.31 |
| Bandwidth | $0.00 |
| **Total** | **$5.46** |

The VM is deallocated, so compute no longer bills, but the static public IP and
the disk still do for as long as they exist.

**2026-10-26:** the subscription (a Free Trial with a spending limit) is now
disabled and read-only. `az vm start` is refused with
`ReadOnlyDisabledSubscription`, so nothing more can be charged or changed
until it's re-enabled. See [the VM page](evidence/azure-vm.md).

## Domain

| Item | Value |
|---|---|
| Domain | `gavinclarke.me` |
| Registrar | Namecheap |
| Cost | $0 (free first year through the GitHub Student Developer Pack) |
| Registered | 2026-10-08 |
| Expires | 2027-10-08 |

Keeping the domain past 2027-10-08 means renewing at Namecheap's regular `.me`
price.

## Other services

| Service | Use | Cost |
|---|---|---|
| Zoho Mail | Email at `gavinclarke.me` | $0 (free plan) |
| Cloudflare | DNS and the `www` redirect | $0 (free plan) |
