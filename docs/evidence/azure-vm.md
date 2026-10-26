# Running the site on the Azure VM

Written on 2026-10-26, from the records made while the VM was the live host
(2026-10-08 to 2026-10-13) and a check on 2026-10-20. The site now runs on
Railway, and the VM is deallocated. The step-by-step records are in
[`operate-the-vm.md`](../superpowers/plans/2026-10-01-operate-the-vm.md) and
[`azure-vm-migration.md`](../superpowers/plans/2026-09-24-azure-vm-migration.md).

## 1. What ran where

```text
visitor ──▶ Azure firewall (NSG) ──▶ nginx :80/:443 ──▶ uvicorn on 127.0.0.1:8000 ──▶ SQLite file
            allows 22 (my IP), 80, 443               2 workers, run by systemd      on the VM's disk
```

| Piece | On the VM |
|---|---|
| VM | `vm-career-platform`, Ubuntu 24.04 LTS, `Standard_B2ts_v2` (2 vCPU, 1 GiB RAM), West US 2 |
| Web server | nginx 1.24.0, the only public entry point, with HTTPS from Certbot |
| App server | uvicorn with `--workers 2`, listening on `127.0.0.1:8000` only |
| Service manager | systemd service `career-platform`, `enabled`, runs as `azureuser` (not root) |
| Database | SQLite, the same engine as on my laptop: `/home/azureuser/career-platform-data/career_platform.db` |

**Same database engine.** I kept SQLite for this first move. I copied the
laptop's database file to the VM and checked both copies with `sha256sum`; the
hashes matched, so the data was identical (see
[Exercise 03](ex03.md), section 3). The app reads the file directly from the
VM's own disk, so its database access is local.

## 2. Access, addresses and network rules

| Item | Value |
|---|---|
| SSH | `ssh -i ~/.ssh/isba4775_azure azureuser@20.114.0.108` (key login, user `azureuser`) |
| Public IP | `20.114.0.108` (static) |
| Private IP | `172.16.0.4`, on virtual network `vnet-westus2-1` (`172.16.0.0/16`) |
| Firewall | NSG `vm-career-platform-nsg`, on the VM's network card |

The NSG's inbound rules, read with `az network nsg rule list` on 2026-10-26:

| Rule | Port | Source | Why |
|---|---|---|---|
| `Alllow-SSH-Laptop` (priority 300) | TCP 22 | `99.7.122.53/32` only | SSH from my home IP and nowhere else |
| `Allow-HTTP-80` (priority 320) | TCP 80 and 443 | Any | Visitors reach nginx. The name says 80, but the rule also opens 443 for HTTPS |

Everything else is blocked by Azure's default deny rule. There is no rule for
port 8000.

**Kept off public ports:**

- **The app** listens on `127.0.0.1:8000`, which only the VM itself can reach.
  From my laptop, `curl -m 8 http://20.114.0.108:8000/health` got no answer
  (`8000 closed`). On the VM, a request to the private IP on port 8000 was
  refused.
- **The database** is a file, not a server, so it has no network port at all.
- **`sudo ss -ltnp`** on 2026-10-08 showed only sshd on 22, nginx on 80, and
  uvicorn on `127.0.0.1:8000`. Certbot later added nginx on 443.
- **nginx** returns 404 for `/admin`, so the unprotected admin page isn't public.

## 3. The site responded and read its database

From my laptop on 2026-10-08, through nginx:

| Check | Result |
|---|---|
| `/`, `/resume`, `/projects`, `/contact`, `/health`, `/static/css/styles.css` | `200` for all six |
| Homepage | `Server: nginx/1.24.0 (Ubuntu)`, page contains `Gavin Clarke` |
| `/health` | `{"status":"ok","database":"healthy","fallback":false}` |
| `/admin` | `404` |

`"fallback": false` means the pages came from the database, not the app's
built-in backup copy. `Gavin Clarke` is the profile stored in the database.
HTTPS also worked: [Exercise 04](ex04.md) shows HTTP redirecting to
`https://gavinclarke.me/` with a 301 from nginx, and the certificate check.

## 4. It came back after restarts

| Test | What happened |
|---|---|
| **Worker crash** (2026-10-08, `kill -9` on one worker) | uvicorn started a new worker within a second. The other worker kept serving, `/health` stayed healthy, and systemd didn't need to restart anything |
| **Whole app crash** (2026-10-08, `kill -9` on uvicorn's main process) | systemd restarted the service 2 seconds later with a new process and 2 new workers. `NRestarts` went from 0 to 1, and `/health` was healthy |
| **VM start from deallocated** (2026-10-20) | I started the stopped VM with `az vm start` and didn't log in. The site answered over HTTPS from `Server: nginx/1.24.0 (Ubuntu)` with `{"status":"ok","database":"healthy","fallback":false}`, so nginx and the app had both started on their own at boot (see [Exercise 03](ex03.md), section 2) |

**What's missing:** I didn't record a timed reboot test, comparing the VM's
boot time (`uptime -s`) with the service's start time. When I tried to run one
on 2026-10-26, Azure refused to start the VM because my free-trial
subscription is now disabled and read-only. The 2026-10-20 start is the
evidence that the site comes back after the VM restarts.

**The subscription matters beyond this test.** The course asks me to keep the
VM until the instructor says otherwise. While the subscription is disabled the
VM can't run, and Azure eventually deletes the resources of a disabled
subscription, including the VM, its disk and the SQLite data. Re-enabling it
(for example by upgrading to pay-as-you-go) would let it run again, but could
cost money.

## 5. What needed configuring

1. **systemd unit** (`/etc/systemd/system/career-platform.service`):
   - `ExecStart` runs uvicorn with `--host 127.0.0.1 --port 8000 --workers 2`.
   - `User=azureuser`, so the app never runs as root.
   - `Restart=always` with `RestartSec=2` brings the app back after a crash.
   - `WantedBy=multi-user.target`, turned on with `systemctl enable`, starts it at boot.
   - `ExecStartPre` refuses to start if the database file is missing or empty, so the app can't quietly create a blank one.
2. **nginx site** (`/etc/nginx/sites-available/career-platform`):
   - `proxy_pass http://127.0.0.1:8000` forwards every request to the app.
   - `proxy_set_header` passes along the visitor's host and address.
   - `location /admin { return 404; }` hides the admin page.
   - The default welcome page was removed.
   - nginx itself is `enabled` in systemd, so it also starts at boot.
3. **Certbot** got the HTTPS certificate for `gavinclarke.me`, set nginx up to
   answer on 443, and redirects HTTP to HTTPS.
4. **Azure NSG**:
   - I added `Allow-HTTP-80` for 80 and 443.
   - I kept SSH limited to my home IP.
   - I never opened 8000. The temporary `Temp-HTTP-8000` rule from the
     first test was removed.
5. **The app's `.env`** sets `DATABASE_URL` to the SQLite file in
   `~/career-platform-data/`. That folder is outside the code folder, so
   `git pull` never touches the data.
