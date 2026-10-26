# DNS records before the Zoho Mail cutover

**Zone:** `gavinclarke.me`
**Captured:** 2026-10-13 21:11 UTC
**Source:** Cloudflare CLI, `cf dns records list --zone gavinclarke.me`
**Record count:** 10

This is the zone as it stood before any Zoho Mail changes. It's the baseline to compare against, and the reference to roll back to if needed.

| Type | Name | Content | Priority | Proxied | TTL | Comment |
|------|------|---------|----------|---------|-----|---------|
| A | `www.gavinclarke.me` | `192.0.2.1` |  | Yes | Auto | Placeholder: Cloudflare redirects www to gavinclarke.me |
| CNAME | `gavinclarke.me` | `dwaascah.up.railway.app` |  | No | Auto |  |
| MX | `gavinclarke.me` | `eforward1.registrar-servers.com` | 10 | No | Auto |  |
| MX | `gavinclarke.me` | `eforward2.registrar-servers.com` | 10 | No | Auto |  |
| MX | `gavinclarke.me` | `eforward3.registrar-servers.com` | 10 | No | Auto |  |
| MX | `gavinclarke.me` | `eforward4.registrar-servers.com` | 15 | No | Auto |  |
| MX | `gavinclarke.me` | `eforward5.registrar-servers.com` | 20 | No | Auto |  |
| TXT | `_railway-verify.gavinclarke.me` | `"railway-verify=48149c2b27f9e92fea5a905944ee82f3170b3aa13fdfdbaf8fecb2993c7cb092"` |  | No | Auto |  |
| TXT | `gavinclarke.me` | `"v=spf1 include:spf.efwd.registrar-servers.com ~all"` |  | No | Auto |  |
| TXT | `gavinclarke.me` | `"zoho-verification=zb01158665.zmverify.zoho.com"` |  | No | 600 |  |

## Records the Zoho change will affect

- **MX (5 records):** these point at the registrar's `eforward1`–`eforward5` forwarding servers. They get replaced by Zoho's MX hosts.
- **SPF TXT** (`v=spf1 include:spf.efwd.registrar-servers.com ~all`): this changes to include Zoho instead.
- **Zoho verification TXT:** already published. Whether Zoho has confirmed the domain needs checking in the Zoho admin console.
- **Missing:** there are no DKIM or DMARC records yet. Zoho needs a DKIM TXT record, and a DMARC record is worth adding too.
- **Not touched:** the web records (the `www` placeholder A record and the apex CNAME to Railway) and the Railway verification TXT.
