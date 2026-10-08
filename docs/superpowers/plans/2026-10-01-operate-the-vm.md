# Operate the VM Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Visitors reach the site at `http://$VM_IP` (no port), it starts on boot and restarts after a crash, port 8000 stays closed to the internet, and the app runs as `azureuser`, not root.

**Architecture:** Two layers on the VM. **systemd** (Linux's service manager) runs the app as a service named `career-platform`: it starts it at boot, runs it as `azureuser`, and restarts it if it dies. The service runs uvicorn with **2 workers**, so if one worker crashes, the other keeps serving while uvicorn replaces the dead one. **nginx** (a web server) listens on public port 80 and forwards each request to the app on `127.0.0.1:8000`, which only the VM itself can reach. You open port 80 in Azure; 8000 is never opened.

**Tech Stack:** Ubuntu 24.04, systemd, nginx (from apt), uvicorn 0.54 (already in the VM's `.venv`), FastAPI, SQLite.

**Spec:** Your request of 2026-10-08 (no separate spec). Builds on `docs/superpowers/plans/2026-09-24-azure-vm-migration.md`, which put the code, `.venv`, `.env` and database on the VM.

## How the pieces fit

```
Internet
   │
Public IP
   │
Network security group: 22 from your laptop, 80 from anyone
   │
Ubuntu VM
   ├── sshd :22
   ├── Nginx :80 ──▶ Uvicorn on 127.0.0.1:8000 ─▶ the .db file
   │                    (two workers, kept running by systemd)
```

A request travels down this picture. Each layer only talks to the one below it.

| Layer | What it does | Set up by |
|---|---|---|
| Public IP | The VM's fixed internet address (static, so it survives a stop/start) | Already there |
| Network security group | Azure's firewall. Lets in SSH (22) from your laptop only and web traffic (80) from anyone. Nothing else, so 8000 stays closed | 22: already there. 80: Task 4 |
| sshd :22 | How you log in to run the steps | Already there |
| Nginx :80 | The public front door. Forwards each request to the app and blocks `/admin` | Task 3 |
| Uvicorn on 127.0.0.1:8000 | The app itself, reachable only from inside the VM. Two workers, so one crash doesn't take the site down; systemd starts it at boot and restarts it, as `azureuser` | Task 2 |
| The .db file | Your data, `~/career-platform-data/career_platform.db`. Unchanged by this plan | Already there |

## VM details (looked up with `az`, read-only, on 2026-10-08)

| Item | Value |
|---|---|
| Subscription | Azure subscription 1 (your only one) |
| Resource group | `rg-career-platform` (westus2) |
| VM | `vm-career-platform`: Ubuntu 24.04 LTS, Standard_B2ts_v2 (2 vCPU, 1 GiB RAM), running |
| Public IP | **Static** (`vm-career-platform-ip`, Standard SKU), so it survives a stop/start. Not written here; Task 1 loads it into `$VM_IP` |
| SSH | `ssh -i ~/.ssh/isba4775_azure azureuser@$VM_IP` (password login is off; Azure's stored key matches your local key) |
| Firewall (NSG) | `vm-career-platform-nsg` on the VM's network card. The subnet has no NSG. One inbound rule today: `Alllow-SSH-Laptop`, TCP 22 from your laptop's IP only, priority 300. No rule for 80 or 8000 |
| Code + `.venv` on VM | `/home/azureuser/career-platform-2-` |
| Database on VM | `/home/azureuser/career-platform-data/career_platform.db` (named in `.env` as an absolute path) |
| How it runs today | By hand: `nohup uv run … uvicorn … --host 127.0.0.1 --port 8000`, PID in `~/uvicorn.pid` |

> **Path note:** you wrote `~/career-platform`. The migration plan's recorded results put the clone at `~/career-platform-2-` and the DB at `~/career-platform-data`, so this plan uses those. Task 1 confirms them before anything changes. If they differ, stop and fix the paths in Tasks 2–3 first.

## Global Constraints

- Service name: `career-platform`. It runs as `User=azureuser`. Nothing app-related runs as root.
- The app binds only `127.0.0.1:8000`. No NSG rule for 8000, ever.
- NSG rule for the site: `Allow-HTTP-80`, priority `320`. You add it in the portal (Task 4). Nothing else in Azure changes.
- Use the existing clone, `.venv`, `.env` and database. Don't edit files in the repo, run `uv sync`, run Alembic or seed anything.
- The service starts from the clone directory, because the app reads `.env`, `templates/` and `static/` relative to its working directory.
- No tests, and no crash/restart/reboot tests (you'll do those). Checks below only look.

## Review Focus

1. **The old hand-started process still holds port 8000.** The service would fail with "address already in use" and keep retrying. Task 2 stops it first and checks the port is free.
2. **`PUT /admin/profile` has no login.** Once port 80 is open, anyone could call it. nginx blocks `/admin` (Task 3), and Task 5 checks it returns `404` from the laptop.
3. **Started from the wrong folder, the app makes an empty database** and `/health` still says healthy. The service sets `WorkingDirectory` and refuses to start if the DB file is missing or empty. Task 5 checks `"fallback": false` and that no stray `.db` file exists.
4. **nginx's "Welcome to nginx" page answers instead of the site.** Task 3 removes the default site, and Task 5 checks the homepage shows your name.
5. **Port 8000 reachable from the internet.** Task 5 checks that `http://$VM_IP:8000` gets no answer from the laptop.

---

### Task 1: Connect and confirm the starting point

**What this is:** Before changing anything, make sure the VM is what the plan expects. Every later step depends on these paths.

- [x] **Step 1: Load the IP and SSH in**
  - **Where:** laptop
  - **Run:**
    ```bash
    export VM_IP=$(az vm show -d -g rg-career-platform -n vm-career-platform --query publicIps -o tsv)
    echo $VM_IP
    ssh -i ~/.ssh/isba4775_azure azureuser@$VM_IP
    ```
  - **Check:** `echo` prints an IP, and you get a `azureuser@vm-career-platform` prompt. If SSH hangs, you're probably not on your laptop's usual network (the SSH rule only allows that one IP).

- [x] **Step 2: Confirm the paths, settings and data**
  - **Where:** VM
  - **Run:**
    ```bash
    ls -d ~/career-platform-2- ~/career-platform-2-/.venv/bin/uvicorn
    grep '^DATABASE_URL=' ~/career-platform-2-/.env
    test -s ~/career-platform-data/career_platform.db && echo "db ok"
    ss -ltnp | grep ':8000'
    ```
  - **Why:** The service file in Task 2 names these exact paths. `ss` shows what's listening on port 8000 right now.
  - **Check:** Both paths are listed; `DATABASE_URL=sqlite:////home/azureuser/career-platform-data/career_platform.db`; `db ok`; and one line with `127.0.0.1:8000` (the hand-started app). If any path differs, **stop** and fix Tasks 2–3 to match.

**Undo this section:** nothing to undo. Task 1 only reads.

**Results**

Run twice from the laptop, with the commands above, unchanged:

| Check | First run (2026-10-08, between the 17:04 UTC reboot and Task 2) | Re-run (2026-10-08, 17:43 UTC, after Tasks 2–4) |
|---|---|---|
| `echo $VM_IP` | ✅ Prints an IP (not recorded here) | ✅ Same |
| SSH prompt | ✅ `azureuser@vm-career-platform` | ✅ Same |
| Clone and `.venv` uvicorn | ✅ Both listed. `~/career-platform` does not exist, so the plan's paths are right | ✅ Both listed |
| `DATABASE_URL` | ✅ `sqlite:////home/azureuser/career-platform-data/career_platform.db` | ✅ Same |
| DB non-empty | ✅ `db ok` | ✅ `db ok` |
| Port 8000 | ⚠️ **Nothing listening.** The plan expected the hand-started app. The VM had rebooted at 17:04 UTC, and `~/uvicorn.log` ended with a clean `Shutting down … Finished server process [3507]`. `~/uvicorn.pid` (3504) pointed at no process | ✅ `127.0.0.1:8000`, owned by the `career-platform` service: `uvicorn` pid 1652 plus 2 `python` workers (1668, 1669) |

- **Ruling from the first run:** since nothing was on 8000, Task 2 Step 2 had nothing to stop. It only removed the stale `~/uvicorn.pid`. Cost if wrong: none, because Step 2's `ss` check still confirmed `8000 free` before the service started.
- **Extra, not in the plan's checks:** `free -m` showed 836 MiB total and 569 MiB available, enough for 2 workers.

### Task 2: Run the app as a systemd service

**What this is:** systemd starts programs at boot and watches them. A short text file (a "unit file") tells it what to run, as which user, from which folder, and to restart it if it exits. You create the file, stop the hand-started copy, then start the service.

- [x] **Step 1: Write the unit file**
  - **Where:** VM
  - **Run:**
    ```bash
    sudo tee /etc/systemd/system/career-platform.service > /dev/null <<'EOF'
    [Unit]
    Description=Career Platform (FastAPI on uvicorn)
    After=network-online.target
    Wants=network-online.target

    [Service]
    User=azureuser
    Group=azureuser
    WorkingDirectory=/home/azureuser/career-platform-2-
    ExecStartPre=/usr/bin/test -s /home/azureuser/career-platform-data/career_platform.db
    ExecStart=/home/azureuser/career-platform-2-/.venv/bin/uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000 --workers 2
    Restart=always
    RestartSec=2

    [Install]
    WantedBy=multi-user.target
    EOF
    ```
  - **Why, line by line:**
    - `User=azureuser`: the app never runs as root. `sudo` is only needed to write the file.
    - `WorkingDirectory`: lets the app find `.env`, `templates/` and `static/`.
    - `ExecStartPre`: refuses to start if the DB is missing or empty, so the app can't quietly create a blank one.
    - `ExecStart`: runs the `.venv`'s uvicorn directly. `uv run` would try to re-sync packages. `--workers 2` means one crash doesn't take the site down: the other worker keeps serving while uvicorn starts a replacement. The VM has 2 CPUs and 1 GiB RAM, which fits 2 workers.
    - `Restart=always`, `RestartSec=2`: if the whole app exits, systemd starts it again 2 seconds later.
    - `WantedBy=multi-user.target`: start at boot (once enabled in Step 3).
  - **Check:** `systemd-analyze verify /etc/systemd/system/career-platform.service` prints nothing (no errors).

- [x] **Step 2: Stop the hand-started app**
  - **Where:** VM
  - **Run:**
    ```bash
    kill $(ss -ltnp | grep ':8000' | grep -o 'pid=[0-9]*' | cut -d= -f2) $(cat ~/uvicorn.pid) 2>/dev/null
    sleep 2; ss -ltn | grep ':8000' || echo "8000 free"
    rm -f ~/uvicorn.pid
    ```
  - **Why:** Only one program can listen on port 8000. Killing by PID (not `pkill -f`) avoids matching your own SSH command. The site is down from here until Step 3, about a minute.
  - **Check:** prints `8000 free`.

- [x] **Step 3: Enable and start the service**
  - **Where:** VM
  - **Run:**
    ```bash
    sudo systemctl daemon-reload
    sudo systemctl enable --now career-platform
    ```
  - **Why:** `daemon-reload` makes systemd read the new file. `enable` turns on start-at-boot; `--now` also starts it right away.
  - **Check:**
    ```bash
    systemctl is-enabled career-platform     # enabled
    systemctl is-active career-platform      # active
    ss -ltnp | grep ':8000'                  # 127.0.0.1:8000 only, never 0.0.0.0
    ps -o user=,pid=,cmd= -p $(paste -sd, /sys/fs/cgroup/system.slice/career-platform.service/cgroup.procs)
                                             # manager + 2 worker lines, every one azureuser
    curl -s http://127.0.0.1:8000/health     # {"status":"ok","database":"healthy","fallback":false}
    ```
    If it isn't active, `journalctl -u career-platform -n 50` shows why.

**Undo this section** (VM). If port 80 is open, undo Tasks 4 and 3 first, or visitors see nginx's "502 Bad Gateway" page while the app is gone.
```bash
sudo systemctl disable --now career-platform           # stop it and turn off start-at-boot
sudo rm /etc/systemd/system/career-platform.service    # delete the unit file
sudo systemctl daemon-reload                           # make systemd forget it
```
- **Check:** `systemctl list-unit-files career-platform.service` prints `0 unit files listed`, and `ss -ltn | grep ':8000' || echo "8000 free"` prints `8000 free`.
- **To get back to running it by hand** (how it ran before this plan; it stops at the next reboot):
  ```bash
  cd ~/career-platform-2-
  if [ -s ~/career-platform-data/career_platform.db ]; then
    nohup uv run --no-dev uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000 > ~/uvicorn.log 2>&1 < /dev/null &
    echo $! > ~/uvicorn.pid
  else
    echo "DB missing or empty, not starting"
  fi
  ```

**Results** (2026-10-08, run from the laptop over SSH)

| Step | What ran | What the check showed |
|---|---|---|
| 1. Unit file | The unit file above, written with `sudo tee` | ✅ `systemd-analyze verify` printed nothing |
| 2. Stop old app | Nothing to kill (see Task 1 results); only `rm -f ~/uvicorn.pid` | ✅ `8000 free` |
| 3. Enable and start | `daemon-reload`, `enable --now career-platform` | ✅ `Created symlink …/multi-user.target.wants/career-platform.service`, then `enabled`, `active` |
| | `ss -ltnp \| grep :8000` | ✅ `127.0.0.1:8000` only, owned by `uvicorn` pid 1652 and `python` pids 1668, 1669 |
| | `ps` over the service's processes | ✅ 4 lines, all `azureuser`: manager 1652, workers 1668 and 1669, and 1667 (`multiprocessing.resource_tracker`) |
| | `curl http://127.0.0.1:8000/health` | ✅ `{"status":"ok","database":"healthy","fallback":false}` |

- **Note:** the plan expected "manager + 2 worker lines". The fourth line is a small helper process Python's `multiprocessing` starts for the workers. It's expected and also runs as `azureuser`.

### Task 3: Put nginx in front on port 80

**What this is:** nginx is a small, sturdy web server. It listens on port 80 (the default for `http://`, so visitors don't type a port) and passes each request to the app on `127.0.0.1:8000`. This keeps the app private to the VM, and lets nginx block paths the public shouldn't reach.

- [x] **Step 1: Install nginx**
  - **Where:** VM
  - **Run:** `sudo apt-get update && sudo apt-get install -y nginx`
  - **Why:** Ubuntu's nginx package installs it as a boot-time service and runs its request-handling processes as the unprivileged `www-data` user. Only its small manager process is root, which it needs to open port 80.
  - **Check:** `systemctl is-enabled nginx` prints `enabled`, and `curl -s http://127.0.0.1 | grep -o 'Welcome to nginx'` prints `Welcome to nginx` (its default page, replaced next).

- [x] **Step 2: Add the site and remove the default**
  - **Where:** VM
  - **Run:**
    ```bash
    sudo tee /etc/nginx/sites-available/career-platform > /dev/null <<'EOF'
    server {
        listen 80 default_server;
        listen [::]:80 default_server;
        server_name _;

        # PUT /admin/profile has no login. Keep it off the public site.
        location /admin { return 404; }

        location / {
            proxy_pass http://127.0.0.1:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
    EOF
    sudo ln -s /etc/nginx/sites-available/career-platform /etc/nginx/sites-enabled/career-platform
    sudo rm /etc/nginx/sites-enabled/default
    sudo nginx -t && sudo systemctl reload nginx
    ```
  - **Why:** `listen 80 default_server` answers any request to the VM's IP. `location /admin` returns "not found" for `/admin` and everything under it. `location /` forwards the rest to the app. The `proxy_set_header` lines pass along the visitor's original address and host. Removing `default` (a link; the original file stays in `sites-available`) stops the welcome page. `nginx -t` checks the config for typos before `reload` applies it.
  - **Check:**
    ```bash
    curl -s http://127.0.0.1/health                                  # same healthy JSON as Task 2
    curl -s http://127.0.0.1/ | grep -o 'Gavin Clarke' | head -1     # Gavin Clarke
    curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1/admin  # 404
    sudo ufw status                                                  # Status: inactive (else: sudo ufw allow 80/tcp)
    ```

**Undo this section** (VM). nginx wasn't installed before this plan, so a full undo removes it. If port 80 is open, undo Task 4 first.
```bash
sudo rm -f /etc/nginx/sites-enabled/career-platform /etc/nginx/sites-available/career-platform   # our site file
sudo systemctl disable --now nginx                     # stop it and turn off start-at-boot
sudo apt-get purge -y nginx nginx-common               # uninstall it and its default config
sudo apt-get autoremove -y                             # remove packages only nginx needed
```
- **Why this order:** `purge` removes the files the package installed, but not files we added, so we delete our site file first.
- **Check:** `command -v nginx || echo "nginx gone"` prints `nginx gone`, and `ss -ltn | grep ':80 ' || echo "80 free"` prints `80 free`. The app on `127.0.0.1:8000` keeps running; only the front door is gone.
- **Lighter option** (keep nginx installed, just show its welcome page again): `sudo rm /etc/nginx/sites-enabled/career-platform && sudo ln -s /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default && sudo nginx -t && sudo systemctl reload nginx`. The welcome page forwards nothing to the app, so `/admin` stays unreachable.

**Results** (2026-10-08, run from the laptop over SSH)

| Step | What ran | What the check showed |
|---|---|---|
| 1. Install | `apt-get update` and `apt-get install -y nginx` | ✅ `apt exit 0`; `systemctl is-enabled nginx` → `enabled`; `curl http://127.0.0.1` → `Welcome to nginx` |
| 2. Site | Site file above, symlink added, `default` removed, `nginx -t`, `reload` | ✅ `syntax is ok`, `test is successful` |
| | `curl http://127.0.0.1/health` | ✅ `{"status":"ok","database":"healthy","fallback":false}` |
| | Homepage `grep 'Gavin Clarke'` | ✅ `Gavin Clarke` |
| | `/admin` | ✅ `404`. Extra check: `PUT /admin/profile` also `404` |
| | `sudo ufw status` | ✅ `Status: inactive`, so no extra firewall rule needed |
| | Extra: `ps -C nginx` | ✅ Master runs as `root`, 2 workers as `www-data` |

- **Ruling:** apt ran with `-qq` and `DEBIAN_FRONTEND=noninteractive`, with output in `/tmp/apt.log` on the VM, so it couldn't stop at a prompt over a one-shot SSH. Same packages as the plan's command. Cost if wrong: none.

### Task 4: Open port 80 in Azure (you, in the portal)

**What this is:** The NSG is Azure's firewall in front of the VM. Right now it only lets SSH in, so the internet can't reach nginx yet.

- [x] **Step 1: Add the rule**
  - **Where:** Azure portal (you click)
  - **Click:** `vm-career-platform` → Networking → Add inbound port rule. Source **Any**, destination port **80**, protocol **TCP**, action **Allow**, priority **320**, name **Allow-HTTP-80**.
  - **Why:** "Any" source because visitors come from anywhere. Only 80 is opened. 8000 stays closed.
  - **Check (laptop, read-only):**
    ```bash
    az network nsg rule list -g rg-career-platform --nsg-name vm-career-platform-nsg \
      --query "[].{name:name,port:destinationPortRange,src:sourceAddressPrefix,access:access,prio:priority}" -o table
    ```
    Shows `Allow-HTTP-80 | 80 | * | Allow | 320` next to the SSH rule, and no rule mentions 8000.

**Undo this section** (you, in Azure). This is the fastest way to take the site off the internet. Everything on the VM keeps running.
- **Portal:** `vm-career-platform` → Networking → Inbound port rules → `Allow-HTTP-80` → Delete.
- **Or CLI (laptop):** `az network nsg rule delete -g rg-career-platform --nsg-name vm-career-platform-nsg -n Allow-HTTP-80`
- **Check (laptop):** the `az network nsg rule list …` command above shows only the SSH rule, and `curl -s -m 8 http://$VM_IP/ > /dev/null || echo "80 closed"` prints `80 closed`.

**Results** (2026-10-08)

| Step | What ran | What the check showed |
|---|---|---|
| Before | `az network nsg rule list` (laptop) | Only `Alllow-SSH-Laptop` (22, priority 300) |
| 1. Add rule | You added it in the portal | ✅ `az network nsg rule list` shows `Allow-HTTP-80`: port 80, source `*`, TCP, Inbound, Allow, priority 320. The SSH rule is unchanged, and no rule mentions 8000 |

### Task 5: Check it from the internet

**What this is:** The real test: your laptop is "the internet". Every check below only reads.

- [x] **Step 1: Check the public site, and that private things stay private**
  - **Where:** laptop
  - **Run:**
    ```bash
    for p in / /resume /projects /contact /health /static/css/styles.css; do
      echo "$(curl -s -o /dev/null -w '%{http_code}' http://$VM_IP$p) $p"; done   # all 200
    curl -s http://$VM_IP/health                                   # "fallback":false
    curl -s -o /dev/null -w '%{http_code}\n' http://$VM_IP/admin   # 404
    curl -s -m 8 http://$VM_IP:8000/health || echo "8000 closed"   # 8000 closed
    ```
  - **Check:** six `200`s, the healthy JSON with `"fallback":false`, `404` for `/admin`, and `8000 closed`. Then open `http://<the IP>` in your browser: the styled homepage with your name.

- [x] **Step 2: Confirm boot start, user, and data**
  - **Where:** VM
  - **Run:**
    ```bash
    systemctl is-enabled career-platform nginx                       # enabled, enabled
    ps -o user=,cmd= -p $(paste -sd, /sys/fs/cgroup/system.slice/career-platform.service/cgroup.procs)   # every line starts with azureuser
    ls ~/career-platform-2-/*.db 2>/dev/null || echo "no stray db"   # no stray db
    ```
  - **Why:** `enabled` is what makes both start at boot (you'll prove it with your own reboot test). The `ps` line proves the app isn't root. "No stray db" proves the app used the real database, not a new empty one.

**Undo this section:** nothing to undo. Task 5 only reads.

**Results** (2026-10-08, right after Task 4)

| Step | What ran | What the check showed |
|---|---|---|
| 1. Public site (laptop) | The six-path loop | ✅ `200` for `/`, `/resume`, `/projects`, `/contact`, `/health`, `/static/css/styles.css` |
| | `curl http://$VM_IP/health` | ✅ `{"status":"ok","database":"healthy","fallback":false}` |
| | `/admin` | ✅ `404`. Extra check: `PUT /admin/profile` also `404` |
| | Extra: homepage | ✅ Contains `Gavin Clarke`; `Welcome to nginx` count `0` |
| | `curl -m 8 http://$VM_IP:8000/health` | ✅ `8000 closed` |
| | Browser | ⏳ For you to look at; I only used `curl` |
| 2. VM | `systemctl is-enabled career-platform nginx` | ✅ `enabled`, `enabled` |
| | `ps` over the service's processes | ✅ 4 lines, all `azureuser` |
| | Stray DB | ✅ `no stray db` |
| | Extra: `sudo ss -ltnp` | ✅ `0.0.0.0:22` and `[::]:22` sshd; `0.0.0.0:80` and `[::]:80` nginx; `127.0.0.1:8000` uvicorn. Nothing else on these ports |

**Final review** (a fresh reviewer, read-only on the live VM): **ready, no required fixes.** It found 0 critical and 0 important issues. It tried 14 variants of `/admin` (all GET, e.g. `//admin`, `/Admin`, `/%61dmin/profile`, `/static/../admin`), and every one returned `404`. Five minor items, none changed yet:
1. systemd's default start limit (5 starts in 10 s) can stop restarts during a fast crash loop. Fix: `StartLimitIntervalSec=0` under `[Unit]`.
2. `/docs`, `/redoc` and `/openapi.json` are public and list the `/admin` routes (the routes themselves still return 404).
3. nginx may answer `502` for a second or two after boot, while the app starts.
4. nginx shows its version in response headers (`server_tokens` is on).
5. Each request is logged twice, by nginx and by uvicorn.

## Full rollback (reverse order)

Undo from the outside in. Close the public door first, so visitors get no answer rather than an error page while things are removed.

1. **Task 4** (Azure): delete `Allow-HTTP-80`. The site is now off the internet.
2. **Task 3** (VM): remove our nginx site and uninstall nginx.
3. **Task 2** (VM): disable and delete the `career-platform` service. Restart by hand if you still want the app running.
4. **Tasks 1 and 5:** nothing to undo. They only read.

This plan never changes your code, `.venv`, `.env` or database, so none of them need restoring. The only thing removed and not put back is the old `~/uvicorn.pid`; the by-hand start command above writes a fresh one.

## Day-to-day commands (VM)

| To… | Run |
|---|---|
| See if it's running | `systemctl status career-platform` |
| Read app logs | `journalctl -u career-platform -n 100` (add `-f` to follow) |
| Restart after a `git pull` | `sudo systemctl restart career-platform` |
| Stop it (stays enabled for next boot) | `sudo systemctl stop career-platform` |

## Restart check

**What this is:** After a reboot or restart, these show when the VM booted, when the service started, and whether the site answers through nginx. Every check only reads.

- **Where:** VM (first block), laptop (second block)
- **Run:**
  ```bash
  uptime -s                                                        # when the VM last booted
  systemctl show career-platform -p ActiveEnterTimestamp,NRestarts,MainPID
  systemctl show nginx -p ActiveEnterTimestamp
  ```
  ```bash
  curl -s -D - -o /tmp/home.html http://$VM_IP/ | grep -i -E '^HTTP|^server'   # 200, Server: nginx
  grep -o 'Gavin Clarke' /tmp/home.html | head -1                              # Gavin Clarke
  curl -s http://$VM_IP/health                                                 # "fallback":false
  ```
- **Check:** after a reboot, the service's start time is within a minute or so of the boot time. If it's much later, the service didn't start at boot; someone started it by hand.

**Results** (2026-10-08, 17:51 UTC)

| Check | What it showed |
|---|---|
| VM last booted | 2026-10-08 17:04:41 UTC (up 46 minutes). This is the reboot from before Task 2 |
| `career-platform` started | 2026-10-08 17:29:30 UTC, main pid 1652, `NRestarts=0`, `enabled`, `active (running)` |
| nginx started | 2026-10-08 17:29:55 UTC, `enabled`, `active` |
| Homepage through nginx (laptop) | ✅ `HTTP/1.1 200 OK`, `Server: nginx/1.24.0 (Ubuntu)`, page contains `Gavin Clarke`, `Welcome to nginx` count `0` |
| Homepage through nginx (on the VM) | ✅ `200`, `Gavin Clarke` |
| `/health` (laptop) | ✅ `{"status":"ok","database":"healthy","fallback":false}` |

- **⚠️ Start-at-boot is not proven yet.** The service started 25 minutes after the boot, because that's when Task 2 ran `enable --now`, not because the VM booted. No reboot has happened since the service was enabled. Your reboot test proves it: afterwards, `uptime -s` and `ActiveEnterTimestamp` should be close together.
- `NRestarts=0`: systemd hasn't had to restart the app since it started.

### Worker crash test

**What this is:** Kill one uvicorn worker (not the main process) with `kill -9`, which can't be caught, like a hard crash. Uvicorn's main process should start a replacement while the other worker keeps serving, and systemd shouldn't have to restart the service.

- **Where:** VM
- **Run:**
  ```bash
  MAIN=$(systemctl show -p MainPID --value career-platform)
  ps -o user,pid,ppid,lstart,cmd --ppid $MAIN -p $MAIN            # before
  W=$(ps -o pid=,cmd= --ppid $MAIN | grep 'multiprocessing.spawn' | head -1 | awk '{print $1}')
  kill -9 $W
  sleep 5
  ps -o user,pid,ppid,lstart,cmd --ppid $MAIN -p $MAIN            # after
  curl -s http://127.0.0.1/health
  systemctl status career-platform --no-pager -n 12
  ```
- **Why:** Workers show as `multiprocessing.spawn` children of the main pid. The `resource_tracker` child isn't a worker, so the `grep` skips it.
- **Check:** the killed pid is gone and a new worker pid has a fresh start time. The main pid and "active (running) since" in `systemctl status` are unchanged. `/health` is healthy.

**Results** (2026-10-08, kill at 17:52:43 UTC)

| Process | Before | After |
|---|---|---|
| Main uvicorn (`--workers 2`) | 1652, started 17:29:29 | 1652, same process |
| Python helper (`multiprocessing.resource_tracker`) | 1667 | 1667 |
| Worker | **1668** | Killed with `kill -9` |
| Worker | 1669 | 1669 |
| Worker | — | **3190**, started 17:52:43 |

All processes ran as `azureuser`, before and after.

| Check | What it showed |
|---|---|
| Service log | ✅ `17:52:43 uvicorn[1652]: Child process [1668] died`, then `17:52:44 uvicorn[3190]: Started server process [3190]` … `Application startup complete.` |
| `systemctl status` | ✅ `active (running) since Thu 2026-10-08 17:29:30 UTC`, the same as before, and main pid `1652`. systemd didn't restart the service; uvicorn replaced the worker itself. 7 tasks, 161.6M memory |
| `/health`, 5 s after the kill | ✅ `{"status":"ok","database":"healthy","fallback":false}` |

- **New worker serving:** worker 1669 answered the `/health` request right after the kill. The service log later shows the new worker 3190 serving visitor requests (`GET /`, `GET /static/css/styles.css`) at 17:53:44–17:53:46, so the replacement works.

### Main process crash test

**What this is:** Kill uvicorn's main process with `kill -9`, like a hard crash, without using `systemctl`. The workers can't run without it, so systemd should stop what's left of the service and start a fresh copy 2 seconds later (`Restart=always`, `RestartSec=2`).

- **Where:** VM
- **Run:**
  ```bash
  MAIN=$(systemctl show -p MainPID --value career-platform)
  systemctl show -p NRestarts --value career-platform              # before
  kill -9 $MAIN
  systemctl status career-platform --no-pager -n 8                 # status #1, right after
  sleep 5
  systemctl status career-platform --no-pager -n 15                # status #2, 5 s later
  systemctl show -p NRestarts --value career-platform              # after: up by 1
  curl -s http://127.0.0.1/health
  ```
- **Check:** status #1 shows the main pid `code=killed, signal=KILL`. Status #2 shows `active (running)` with a new main pid, a fresh "since" time and 2 new workers. `NRestarts` has gone up by 1, and `/health` is healthy.

**Results** (2026-10-08, kill at 17:54:10.209 UTC)

| Check | Status #1 (17:54:10.211, 2 ms after the kill) | Status #2 (17:54:15.223, 5 s later) |
|---|---|---|
| `Active` | `deactivating (stop-sigterm) (Result: signal)` | ✅ `active (running) since Thu 2026-10-08 17:54:12 UTC` |
| Main PID | `1652 (code=killed, signal=KILL)` | ✅ `3291 (uvicorn)` |
| Processes | 1667 (resource_tracker) and workers 1669 and 3190, still running while systemd stops them | ✅ All new: 3291 (main), 3292 (resource_tracker), workers 3293 and 3294 |
| `ExecStartPre` (DB check) | — | ✅ `status=0/SUCCESS` |
| Log | `Main process exited, code=killed, status=9/KILL` | ✅ `Scheduled restart job, restart counter is at 1`, `Started career-platform.service`, both workers `Application startup complete` at 17:54:13 |

| Check | What it showed |
|---|---|
| `NRestarts` | ✅ `0` before, `1` after |
| `/health` after | ✅ `{"status":"ok","database":"healthy","fallback":false}` |

- **Downtime:** about 3 seconds, from the kill (17:54:10) until both new workers were ready (17:54:13). nginx would have answered `502 Bad Gateway` to requests in that window.
- **Unlike the worker test,** this restarted the whole service: new main pid, new "since" time, and `NRestarts` went up.

## Self-review against your request

| You asked for | Where |
|---|---|
| `http://PUBLIC-IP`, no port | Task 3 (nginx on 80), Task 4 (NSG), Task 5 Step 1 |
| Starts on boot | Task 2 Step 3 and Task 3 Step 1 (`enabled`), Task 5 Step 2 |
| Comes back after a crash | `Restart=always` (Task 2 Step 1). Your crash tests verify it |
| One crash doesn't take the site down | `--workers 2` (Task 2 Step 1); Task 2 Step 3 checks for 2 workers (the `ps` line lists every process systemd started for the service; workers show as `python`) |
| Port 8000 closed | `--host 127.0.0.1` (Task 2), no NSG rule (Task 4), Task 5 Step 1 |
| Not root | `User=azureuser` (Task 2); `ps` checks in Tasks 2 and 5 |
| Service named `career-platform`; rule `Allow-HTTP-80` at 320 | Tasks 2 and 4 |
| Existing code, `.venv`, DB; no repo edits or tests | Global Constraints; only files in `/etc` are created |
