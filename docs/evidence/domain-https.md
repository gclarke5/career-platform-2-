# Domain and HTTPS

Written on 2026-10-26. The checks below were run that day from my laptop.

## 1. The domain and its DNS

| Item | Value |
|---|---|
| Domain | `gavinclarke.me`, registered at Namecheap (free with the GitHub Student Pack), expires 2027-10-08 |
| Authoritative DNS | Cloudflare: `liz.ns.cloudflare.com` and `sevki.ns.cloudflare.com`, set as the name servers at Namecheap |

## 2. The records

| Name | Type | Value | Proxy | Purpose |
|---|---|---|---|---|
| `@` (`gavinclarke.me`) | CNAME | `dwaascah.up.railway.app` | DNS only | Sends the bare domain straight to Railway, so Railway serves the site and its certificate |
| `_railway-verify` | TXT | `railway-verify=4814…b092` | — | Proves to Railway that I own the domain |
| `www` | A | `192.0.2.1` (placeholder) | Proxied | Lets Cloudflare's redirect rule answer `www`. The placeholder address is never contacted |
| `@` | MX | `mx.zoho.com` (10), `mx2.zoho.com` (20), `mx3.zoho.com` (50) | — | Email to `@gavinclarke.me` goes to Zoho Mail |
| `@` | TXT | `v=spf1 include:zohomail.com ~all` | — | SPF: Zoho may send mail for the domain |
| `@` | TXT | `zoho-verification=…` | — | Proves to Zoho that I own the domain |
| `zmail._domainkey` | TXT | `v=DKIM1; k=rsa; p=…` | — | DKIM key that signs mail sent through Zoho |
| `_dmarc` | TXT | `v=DMARC1; p=none; rua=mailto:career-platform@gavinclarke.me` | — | DMARC: report on failing mail, but don't block it yet |

The email records are covered in [Exercise 06](ex06.md).

**Why the site record is DNS only:** with the grey cloud, Cloudflare only
answers the DNS question and doesn't sit in the traffic. Visitors connect
straight to Railway, and Railway's certificate is the one they see. A bare
domain can't hold a normal CNAME, so Cloudflare "flattens" it: it looks up
Railway's address and answers with that A record (`69.46.46.23`).

**Why `www` is proxied:** Railway's trial allows one custom domain per service,
and the bare domain uses it. So `www` never reaches Railway. A Cloudflare
redirect rule only runs on traffic that passes through Cloudflare, so `www` has
to be proxied (orange cloud). The rule "Redirect www to the root domain" answers
every `www` request with a 301 to `https://gavinclarke.me`, keeping the path and
query string.

## 3. Verification

**DNS**, asked directly of Cloudflare's name server:

```text
$ dig +short NS gavinclarke.me
sevki.ns.cloudflare.com.
liz.ns.cloudflare.com.
$ dig +short @sevki.ns.cloudflare.com gavinclarke.me A
69.46.46.23
$ dig +short dwaascah.up.railway.app
69.46.46.23
$ dig +short @sevki.ns.cloudflare.com www.gavinclarke.me A
172.67.163.156
104.21.10.150
```

The bare domain resolves to the same address as the Railway target, and `www`
resolves to Cloudflare's edge, not to the placeholder.

**HTTP and HTTPS:**

| Request | Result | Answered by |
|---|---|---|
| `http://gavinclarke.me/` | 301 → `https://gavinclarke.me/` | Railway (`69.46.46.23`) |
| `https://gavinclarke.me/` | 200, certificate verifies | Railway (`server: railway-hikari`) |
| `http://www.gavinclarke.me/` | 301 → `https://gavinclarke.me/` (one hop), final page 200 | Cloudflare (`server: cloudflare`) |
| `https://www.gavinclarke.me/` | 301 → `https://gavinclarke.me/`, certificate verifies | Cloudflare |
| `https://www.gavinclarke.me/projects?x=1` | 301 → `https://gavinclarke.me/projects?x=1` | Cloudflare |

So both `http://www` and `https://www` land on the root address with a valid
certificate, and the path and query come along.

## 4. Certificates

| | `gavinclarke.me` | `www.gavinclarke.me` |
|---|---|---|
| Served by | Railway | Cloudflare (the proxied record) |
| Hostnames (SAN) | `gavinclarke.me` | `*.gavinclarke.me`, `gavinclarke.me` |
| Issuer | Let's Encrypt (`YE1`) | Let's Encrypt (`YE1`) |
| Valid | 2026-10-13 to 2027-01-11 (90 days) | 2026-10-08 to 2027-01-06 (90 days) |
| `openssl` verify | `0 (ok)` | `0 (ok)` |
| Renewal | Railway renews it automatically while the domain points at Railway | Cloudflare's Universal SSL renews it automatically while `www` is proxied |

Checked with:

```bash
echo | openssl s_client -connect gavinclarke.me:443 -servername gavinclarke.me 2>/dev/null \
  | openssl x509 -noout -subject -issuer -dates -ext subjectAltName
```

Neither certificate needs anything from me. If the bare domain stopped
pointing at Railway, Railway couldn't renew its certificate, and it would
expire on 2027-01-11.

## 5. The move from Azure to Railway

| | On the Azure VM (2026-10-08 to 2026-10-13) | On Railway (since 2026-10-13) |
|---|---|---|
| `@` record | A → `20.114.0.108`, DNS only | CNAME → `dwaascah.up.railway.app`, DNS only |
| Certificate | Let's Encrypt from Certbot on the VM. Renewal was left to Certbot's automatic timer, but I never recorded a check of it (see below) | Let's Encrypt from Railway, renewed by Railway |
| Server header | `nginx/1.24.0 (Ubuntu)` | `railway-hikari` |

On 2026-10-13 I changed `@` in Cloudflare from the VM's A record to the Railway
CNAME, added the `_railway-verify` TXT record, and set up `www` with the
redirect rule. Railway issued the bare domain's certificate. The
checks right after the switch (in the
[migration plan](../superpowers/plans/2026-10-08-railway-postgres-migration.md))
matched today's: the bare domain resolved to `69.46.46.23` on Cloudflare,
Google and Quad9 DNS, `http://` redirected to `https://`, and `www`
redirected to the root in one hop. [Exercise 04](ex04.md) shows the HTTPS check
from when the VM served the site.

Since the VM stopped, no record points to it, and the site keeps one address:
`https://gavinclarke.me`.

**Not verified: renewal on the VM.** I didn't save `sudo certbot renew
--dry-run` or `systemctl list-timers certbot.timer` output while the VM was
the live host. [Exercise 04](ex04.md) shows the HTTPS redirect and how I
checked the certificate, but not its dates. The check can't be run now,
because the Azure subscription is disabled. Renewal only runs while the VM is
on, so after any long shutdown the README's VM rollback starts with
`sudo certbot renew`.
