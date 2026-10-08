# Azure VM Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run the career platform on the Azure VM `vm-career-platform`, serving the SQLite data from your laptop, and prove it answers on the VM.

**Architecture:** One Ubuntu VM, reached over SSH. Code is cloned from GitHub. `uv` builds the Python environment from the committed `uv.lock`. Config comes from a `.env` copied from `.env.example`. The SQLite file is scp'd from the laptop into a data directory outside the git clone, so a re-clone can't delete it. Uvicorn runs in the background on `127.0.0.1:8000`, and you view it from the laptop through an SSH tunnel, so no Azure firewall (NSG) rule changes.

**Tech Stack:** Azure VM (Ubuntu), apt, git, sqlite3, uv, Python 3.12+, FastAPI, Uvicorn, SQLAlchemy, Alembic.

**Spec:** `docs/superpowers/specs/resume-career-platform-spec.md` (deployment target), plus your eight-category migration plan (the section order below).

## Connection facts (used in every step)

| Item | Value |
|---|---|
| Resource group | `rg-career-platform` |
| VM | `vm-career-platform` |
| Public IP | `20.114.0.108` (commands use `$VM_IP`, set in S1, because a deallocate can change it) |
| SSH user | `azureuser` |
| SSH key | `~/.ssh/isba4775_azure` |
| SSH command | `ssh -i ~/.ssh/isba4775_azure azureuser@$VM_IP` |
| Repo (public) | `https://github.com/gclarke5/career-platform-2-.git` |
| Clone path on VM | `/home/azureuser/career-platform-2-` |
| Data dir on VM | `/home/azureuser/career-platform-data` |
| DB path on VM | `/home/azureuser/career-platform-data/career_platform.db` |

Every step lists **Where** (laptop, VM or portal), **Run**, **Why**, **Check** and **Undo**. "VM" means inside the SSH session above. "Portal" means *you* click in the Azure portal. The agent can't click, so it stops and waits at those steps.

**Undo baseline:** The Codespace still has the original code and DB, and GitHub still has the code. Nothing in this plan modifies either one, or the source DB on your laptop. For almost every step the real rollback is "throw away what we made on the VM; the Codespace still has the original." Each **Undo** line only cleans up what that step made on the VM (or a temp file on the laptop). The full rollback is at the end.

**Section order:** Sections 1–8 are your eight categories, in your order. Steps you didn't list go *inside* the matching section, and the table under "Steps you didn't predict" lists each one. Stopping the VM afterwards is an appendix, not a ninth section.

## Global Constraints

- Always SSH and scp as `azureuser` with `-i ~/.ssh/isba4775_azure`.
- The app reads `.env` from the **current working directory** (`app/config.py`: `env_file=".env"`). Templates and static files are also relative (`app/main.py`, `app/routes/public.py`). Always start uvicorn from `~/career-platform-2-`.
- The VM's `DATABASE_URL` must be absolute, with four slashes: `sqlite:////home/azureuser/career-platform-data/career_platform.db`. The template's default `sqlite:///./career_platform.db` depends on the working directory.
- Start the app with the factory: `app.main:create_app --factory` (from `README.md`).
- Python `>=3.12` (`pyproject.toml`).
- **No step creates or seeds a database.** The only DB on the VM is the scp'd copy of yours. SQLite silently creates an empty file when something opens a path that doesn't exist, and an empty DB still passes `/health`. So: no `alembic upgrade` on the VM (D2's laptop-side upgrade of an old-schema copy is the only exception), no `seed_database()`, no tests on the VM (`uv sync --no-dev`), every `sqlite3` on the VM uses `-readonly`, and R1 won't start without a non-empty DB file.
- Never commit a `.db` file. The `.gitignore` lines for `career_platform.db*` are in your working copy but **not committed**. This plan makes no commits.

## Review Focus

Failure modes most likely to bite that the happy path won't show:

1. **Your laptop's only DB file is empty.** `data/career_platform.db` is 0 bytes (dated 2026-09-29), and a search of your home folder finds no other `career_platform.db`. Copying it would migrate nothing, and the site would still look fine (see #2). D1 refuses an empty source. The real data is most likely in the Codespace (the README runs the app there), and D1 says how to download it. **Data can't run until D1 finds a real file.**
2. **The pages show fallback data whatever the DB holds.** `/`, `/resume`, `/projects` and `/contact` read `app/fallback_data.py` (`get_profile_payload()` gets no DB session). Only `/health` touches the DB, and only with `SELECT 1`. "The site shows my data" can't be judged by eye. V2 proves it with row counts, a content hash and the file the process has open. Making the pages read the DB is a code change, out of scope here.
3. **A wrong or relative `DATABASE_URL` silently creates an empty DB.** `/health` still reports `healthy`. D3 checks that the scp target equals the `.env` path, and V2 checks the open file and that no stray `.db` exists.
4. **A plain copy of a live SQLite file can be torn.** If the app or a DB browser has it open, changes may still be in `-wal`. D2 uses `sqlite3 .backup` for a consistent snapshot.
5. **Uvicorn dies with the SSH session, or after a reboot.** R1 uses `nohup`, and V4 tests a logout. A reboot or deallocate still stops it (and may change the IP). Redo S1 and R1 after any restart.

## Steps you didn't predict

| Step | What it adds | Question for you |
|---|---|---|
| S2 | Confirms the NSG allows port 22 | None (read-only). |
| K1 | Records which packages were already installed, so Undo doesn't remove a preinstalled git | Worth a small file on the VM? |
| G1 check | Compares commit IDs: laptop `HEAD` = `origin/main` = VM `HEAD` | None. |
| P1 | Installs uv on the VM (your plan says "uv" but not how it gets there) | OK to use the official `curl … \| sh` installer? |
| C1 edits | Changes `DATABASE_URL` to the absolute data-dir path and `ENVIRONMENT=production` after the copy | None. Without this the app opens the wrong file. |
| D1 | Finds a **non-empty** DB, downloading it from the Codespace if the laptop has none | **Is your real DB in the Codespace?** The only one on the laptop is 0 bytes. |
| D2 | `sqlite3 .backup` snapshot, plus row counts and a content hash | None. V2 needs these to compare against. |
| D4 | Checks the copy's integrity on the VM | None. |
| R1 guard | Refuses to start uvicorn without the DB file | None. |
| V2–V4 | Proves the process uses your file, opens a browser tunnel, survives logout | Do you need the browser view (V3) or the logout test (V4)? |
| Appendix X | Stops uvicorn and deallocates the VM | Do you want the VM off afterwards, or left running? |

## Review checklist: where each item is covered

| Look for | Where in this plan |
|---|---|
| Your sections, in your order | Sections 1–8 are your eight categories, unchanged. Shutdown is an appendix, not a ninth section (see "Section order") |
| Server steps marked as done | Section 1 status note. S1–S3 only confirm |
| Steps you didn't predict | The table above |
| A reason on every step | Every step's **Why** line (20 of 20 steps) |
| A check on every step | Every step's **Check** line (20 of 20) |
| Code's check compares commit IDs | G1: laptop `HEAD` = `origin/main` = VM `HEAD` |
| A rollback on every step | Every step's **Undo** line (20 of 20), plus the Undo baseline: the Codespace still has the original |
| No step creates or seeds a database | Global Constraints. No `alembic upgrade`/seed, `--no-dev` (P2), `-readonly` sqlite3 on the VM, R1 guard. C1 makes only an empty *directory* |
| Data's scp target matches `.env` | D3 compares the two paths and copies only on a match |
| Verify compares your data, not just a health check | V2: the file the process has open, row counts, dump hash and profile name, all compared with D2 |
| Shutdown deallocates and checks the power state | X2: must print `VM deallocated`. `VM stopped` still bills |
| Portal steps marked as portal | S1, S2, X2: **Where: portal (you click)** |

---

## 1. Server

### Task S: Confirm the VM is running and reachable over SSH

> **Status: already done.** The resource group, VM, public IP, NSG, `azureuser` and key already exist. This section creates nothing. It only confirms they still work. If a check fails, stop and ask. Don't recreate anything.

- [ ] **S1: Confirm the VM is running and pin its IP**
  - **Where:** portal (you click). The `az` line runs on the laptop.
  - **Run/click:** Portal → Resource groups → `rg-career-platform` → `vm-career-platform` → Overview. If Status isn't **Running**, click **Start**. Then in each laptop terminal you'll use:
    ```bash
    export VM_IP=20.114.0.108
    az vm show -d -g rg-career-platform -n vm-career-platform --query "[powerState, publicIps]" -o tsv
    ```
  - **Why:** Every later step needs a running VM at a known IP.
  - **Check:** The output is `VM running` and `20.114.0.108`. If the IP differs, run `export VM_IP=<new IP>`.
  - **Undo:** If you started it here and want it off, use Appendix X2 (deallocate).

- [ ] **S2: Confirm the NSG allows SSH**
  - **Where:** portal (you click)
  - **Run/click:** `vm-career-platform` → Networking → Inbound port rules.
  - **Why:** Every later step uses SSH or scp. This plan doesn't open 8000 (V3 tunnels instead).
  - **Check:** There's an **Allow** rule for TCP 22, ideally limited to your IP.
  - **Undo:** Nothing to undo. This step only reads.

- [ ] **S3: Fix key permissions and log in**
  - **Where:** laptop
  - **Run:**
    ```bash
    chmod 600 ~/.ssh/isba4775_azure
    ssh -i ~/.ssh/isba4775_azure azureuser@$VM_IP 'whoami && hostname && lsb_release -ds && df -h ~'
    ```
  - **Why:** SSH rejects keys that other users can read. This one line proves the login works and shows the OS and free disk space.
  - **Check:** It prints `azureuser`, a hostname, an Ubuntu version and free space. Accept the host fingerprint on the first connection.
  - **Undo:** `chmod` is fine to leave as it is. To forget the host key: `ssh-keygen -R $VM_IP`.

## 2. Packages

### Task K: Install git and sqlite3 with apt-get

- [ ] **K1: Record what's already installed**
  - **Where:** VM
  - **Run:** `dpkg -l git sqlite3 2>/dev/null | grep ^ii | tee ~/preinstalled-packages.txt`
  - **Why:** Ubuntu images often ship git. Undo should remove only what *we* install.
  - **Check:** The file exists. It may list git, or be empty.
  - **Undo:** `rm ~/preinstalled-packages.txt`

- [ ] **K2: Install the packages**
  - **Where:** VM
  - **Run:**
    ```bash
    sudo apt-get update
    sudo apt-get install -y git sqlite3
    ```
  - **Why:** git clones the code. sqlite3 checks the migrated DB (D4, V2).
  - **Check:** `git --version && sqlite3 --version` both print versions.
  - **Undo:** For each package *not* in `~/preinstalled-packages.txt`: `sudo apt-get remove -y <pkg> && sudo apt-get autoremove -y`.

## 3. Code

### Task G: Clone the repository

- [ ] **G1: Clone from GitHub**
  - **Where:** VM (the check also runs on the laptop)
  - **Run:**
    ```bash
    cd ~ && git clone https://github.com/gclarke5/career-platform-2-.git
    ```
  - **Why:** Puts the app code, `pyproject.toml`, `uv.lock` and `.env.example` on the VM. All three are already on `origin/main` (commits `266921b` and `7cf36bc`).
  - **Check:** All three commit IDs must be identical:
    ```bash
    # laptop
    git fetch origin && git rev-parse HEAD origin/main
    # VM
    git -C ~/career-platform-2- rev-parse HEAD
    ```
    If the laptop's `HEAD` and `origin/main` differ, you have unpushed commits and the VM is missing them. Push first, then `git -C ~/career-platform-2- pull` on the VM. (As of writing, both are `7cf36bc`.) The repo is public, so no credentials are needed.
  - **Undo:** `rm -rf ~/career-platform-2-` (the DB lives outside it).

## 4. Python

### Task P: Install uv and sync from the lock file

- [ ] **P1: Install uv on the VM**
  - **Where:** VM
  - **Run:**
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source $HOME/.local/bin/env
    ```
  - **Why:** uv installs a matching Python 3.12+ and the locked packages without touching the system Python.
  - **Check:** `uv --version` prints a version, in this session and in a fresh SSH session.
  - **Undo:** `uv cache clean; rm -rf ~/.local/share/uv; rm ~/.local/bin/uv ~/.local/bin/uvx`. Then delete the line the installer added to `~/.bashrc`/`~/.profile` that sources `$HOME/.local/bin/env`.

- [ ] **P2: Sync the environment**
  - **Where:** VM
  - **Run:**
    ```bash
    cd ~/career-platform-2-
    uv sync --locked --no-dev
    ```
  - **Why:** `--locked` fails instead of quietly re-resolving if `uv.lock` doesn't match `pyproject.toml`, so the VM gets exactly the committed versions. `--no-dev` leaves out pytest and httpx. Tests don't run on the VM, because they open whatever DB is configured.
  - **Check:**
    ```bash
    uv run python -c "import fastapi, sqlalchemy, uvicorn, alembic, jinja2; print('ok')"   # prints ok
    uv run python -c "import pytest"                                                         # ModuleNotFoundError
    ls ~/career-platform-2-/*.db 2>/dev/null || echo "no db"                                 # prints no db
    ```
  - **Undo:** `rm -rf ~/career-platform-2-/.venv`

## 5. Config

### Task C: Create `.env` from `.env.example`

- [ ] **C1: Copy the template and point it at the data dir**
  - **Where:** VM
  - **Run:**
    ```bash
    cd ~/career-platform-2-
    mkdir -p ~/career-platform-data
    cp .env.example .env
    sed -i 's|^DATABASE_URL=.*|DATABASE_URL=sqlite:////home/azureuser/career-platform-data/career_platform.db|' .env
    sed -i 's|^ENVIRONMENT=.*|ENVIRONMENT=production|' .env
    chmod 600 .env
    ```
  - **Why:** `.env.example` documents the three settings in `app/config.py`. Its `DATABASE_URL` is relative, so we replace it with an absolute path outside the clone. That way the app always opens the same file, and that file survives a re-clone.
  - **Check:** `uv run python -c "from app.config import settings; print(settings.database_url, settings.environment)"` prints the four-slash absolute URL and `production`. This only reads settings. It doesn't open the DB.
  - **Undo:** `rm ~/career-platform-2-/.env; rmdir ~/career-platform-data` (`rmdir` only succeeds while the directory is empty).

## 6. Data

### Task D: scp the SQLite database from the laptop

- [ ] **D1: Find the real laptop DB** ⚠️ blocker, see Review Focus #1
  - **Where:** laptop
  - **Run:**
    ```bash
    find ~ \( -name '*.db' -o -name '*.sqlite' -o -name '*.sqlite3' \) -size +0 -not -path '*/.venv/*' -not -path '*/Library/*' 2>/dev/null | xargs ls -lt 2>/dev/null | head -20
    ```
    Then set the one that holds your data:
    ```bash
    export LAPTOP_DB=/full/path/to/your.db
    test -s "$LAPTOP_DB" && sqlite3 -readonly "$LAPTOP_DB" "SELECT full_name FROM profiles;"
    ```
  - **Why:** The repo's `data/career_platform.db` is 0 bytes and is the only `career_platform.db` on the laptop. Migrating it would move nothing. `-size +0` and `test -s` skip empty files. `-readonly` means a typo fails instead of creating a file.
  - **If the laptop has no real copy (likely, see Review Focus #1):** The README runs the app in a Codespace, so your data most likely lives there. Download a copy to the laptop in the browser: github.com/codespaces → open the codespace for `career-platform-2-` → in the Explorer, find `career_platform.db` (repo root, or `data/`) → right-click → **Download…** → save it as `~/Downloads/career_platform_from_codespace.db`. First stop the app in the Codespace terminal (Ctrl-C), so the download isn't missing changes that are still in the `-wal` file. Then `export LAPTOP_DB=~/Downloads/career_platform_from_codespace.db` and run the check below. (`gh codespace cp` does the same thing, but `gh` isn't installed on your laptop.)
  - **Check:** `LAPTOP_DB` points to a non-empty file, and the query prints *your* name, not `Alex Morgan` (the fallback/seed profile). If neither the laptop nor the Codespace has one, **stop and ask**. There's no data to migrate yet.
  - **Undo:** Nothing to undo. This step only reads. Delete the downloaded copy if you made one. The Codespace still has the original.

- [ ] **D2: Take a consistent snapshot and record its contents**
  - **Where:** laptop
  - **Run:**
    ```bash
    sqlite3 -readonly "$LAPTOP_DB" ".backup /tmp/career_platform_upload.db"
    sqlite3 -readonly /tmp/career_platform_upload.db "PRAGMA integrity_check; SELECT version_num FROM alembic_version;"
    for t in profiles experiences projects skills education volunteer_work certifications links site_meta; do
      echo "$t $(sqlite3 -readonly /tmp/career_platform_upload.db "SELECT COUNT(*) FROM $t;")"
    done | tee /tmp/laptop_counts.txt
    sqlite3 -readonly /tmp/career_platform_upload.db .dump | shasum -a 256 | cut -d' ' -f1 | tee /tmp/laptop_dump.sha
    ```
  - **Why:** `.backup` folds any pending `-wal` changes into one self-contained file. A plain file copy doesn't. The counts and the hash are what D4 and V2 compare against.
  - **Check:** `integrity_check` prints `ok`, `alembic_version` prints `c7e1a9d3f2b8`, and the counts aren't all zero.
  - **If `alembic_version` prints `b2c04cf6e9d4`:** the DB predates the `volunteer_work` table, and the count loop prints `no such table: volunteer_work`. Upgrade the *laptop* copy (`alembic.ini` hardcodes `./career_platform.db`, so this points alembic at `$LAPTOP_DB` instead), then redo D2:
    ```bash
    cd ~/Github/career-platform/career-platform-2-
    cp "$LAPTOP_DB" "$LAPTOP_DB.pre-volunteer"
    uv run python -c "import os; from alembic import command; from alembic.config import Config; c = Config('alembic.ini'); c.set_main_option('sqlalchemy.url', 'sqlite:///' + os.environ['LAPTOP_DB']); command.upgrade(c, 'head')"
    ```
    This is the plan's only migration, and it runs on the laptop, never on the VM (Global Constraints). Undo: `mv "$LAPTOP_DB.pre-volunteer" "$LAPTOP_DB"`.
  - **Undo:** `rm /tmp/career_platform_upload.db /tmp/laptop_counts.txt /tmp/laptop_dump.sha`. The source was only read.

- [ ] **D3: scp the snapshot to the exact path in `.env`**
  - **Where:** laptop
  - **Run:**
    ```bash
    TARGET=/home/azureuser/career-platform-data/career_platform.db
    ENV_PATH=$(ssh -i ~/.ssh/isba4775_azure azureuser@$VM_IP \
      "grep '^DATABASE_URL=' ~/career-platform-2-/.env | sed 's|^DATABASE_URL=sqlite:///||'")
    echo "env:    $ENV_PATH"; echo "target: $TARGET"
    if [ "$ENV_PATH" = "$TARGET" ]; then
      scp -i ~/.ssh/isba4775_azure /tmp/career_platform_upload.db azureuser@$VM_IP:$TARGET
    else
      echo "MISMATCH, not copying"
    fi
    ```
  - **Why:** The app opens only the file named in `.env`. A copy anywhere else, or under another name, is ignored, and the app would create an empty DB at the `.env` path.
  - **Check:** No `MISMATCH` line, and `shasum -a 256 /tmp/career_platform_upload.db` (laptop) equals `sha256sum ~/career-platform-data/career_platform.db` (VM).
  - **Undo:** VM: `rm ~/career-platform-data/career_platform.db`

- [ ] **D4: Check the copy on the VM**
  - **Where:** VM
  - **Run:**
    ```bash
    chmod 600 ~/career-platform-data/career_platform.db
    sqlite3 -readonly ~/career-platform-data/career_platform.db "PRAGMA integrity_check;"
    for t in profiles experiences projects skills education volunteer_work certifications links site_meta; do
      echo "$t $(sqlite3 -readonly ~/career-platform-data/career_platform.db "SELECT COUNT(*) FROM $t;")"
    done
    ```
  - **Why:** Confirms the file arrived intact and `azureuser` can read it.
  - **Check:** It prints `ok`, and the counts match `/tmp/laptop_counts.txt` line for line.
  - **Undo:** Same as D3.

## 7. Processes

### Task R: Start uvicorn

- [ ] **R1: Start uvicorn in the background (guarded)**
  - **Where:** VM
  - **Run:**
    ```bash
    cd ~/career-platform-2-
    if [ -s ~/career-platform-data/career_platform.db ]; then
      nohup uv run uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000 > ~/uvicorn.log 2>&1 &
      echo $! > ~/uvicorn.pid
    else
      echo "DB missing or empty, not starting (redo D3)"
    fi
    ```
  - **Why:** Starting from the clone lets the app find `.env`, `static/` and `templates/`. `nohup` keeps it running after you log out. `127.0.0.1` keeps it off the internet. The guard stops SQLAlchemy creating an empty DB on the first `/health` call.
  - **Check:** `tail -n 20 ~/uvicorn.log` shows `Uvicorn running on http://127.0.0.1:8000`, and `ss -ltnp | grep 8000` shows a listener.
  - **Undo:** `pkill -f 'uvicorn app.main:create_app'; rm -f ~/uvicorn.pid`

## 8. Verify

### Task V: The site answers on the VM and shows your data

- [ ] **V1: The pages answer on the VM**
  - **Where:** VM
  - **Run:**
    ```bash
    for p in / /resume /projects /contact /health /static/css/styles.css; do
      echo "$p $(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000$p)"
    done
    ```
  - **Why:** Proves every public route and the static files are served.
  - **Check:** Every line ends in `200`.
  - **Undo:** Nothing to undo. This step only reads.

- [ ] **V2: The running app uses *your* data**
  - **Where:** VM (compare with the laptop's `/tmp/laptop_counts.txt` and `/tmp/laptop_dump.sha`)
  - **Run:**
    ```bash
    DB=~/career-platform-data/career_platform.db
    curl -s http://127.0.0.1:8000/health; echo
    for p in $(pgrep -f 'uvicorn app.main:create_app'); do ls -l /proc/$p/fd 2>/dev/null; done | grep '\.db'
    for t in profiles experiences projects skills education volunteer_work certifications links site_meta; do
      echo "$t $(sqlite3 -readonly $DB "SELECT COUNT(*) FROM $t;")"
    done
    sqlite3 -readonly $DB .dump | sha256sum | cut -d' ' -f1
    sqlite3 -readonly $DB "SELECT full_name, headline FROM profiles;"
    ls ~/career-platform-2-/*.db 2>/dev/null || echo "no stray db"
    ```
  - **Why:** The pages render fallback data whatever the DB holds (Review Focus #2), and `/health` passes on an empty DB. This proves the process has *your* file open, and that the file is byte-for-byte your snapshot.
  - **Check:**
    - `/health` returns `{"status":"ok","database":"healthy","fallback":false}`.
    - The `/proc` line points to `/home/azureuser/career-platform-data/career_platform.db` and nothing else. If nothing is listed, run the `/health` curl again (the connection opens lazily), then repeat.
    - The counts match `/tmp/laptop_counts.txt`, and the hash matches `/tmp/laptop_dump.sha`.
    - The profile row is yours, not `Alex Morgan`.
    - The last line prints `no stray db`.

    If anything doesn't match, stop and find out why.
  - **Undo:** Nothing to undo. This step only reads.

- [ ] **V3: View it in your laptop browser through an SSH tunnel**
  - **Where:** laptop
  - **Run:** `ssh -i ~/.ssh/isba4775_azure -N -L 8000:127.0.0.1:8000 azureuser@$VM_IP`, then open `http://localhost:8000`
  - **Why:** You see the real site without exposing port 8000. A public URL (NSG rule, reverse proxy, systemd) is a separate follow-up.
  - **Check:** The homepage renders with styling, and `http://localhost:8000/health` shows `"fallback": false`.
  - **Undo:** Press Ctrl-C in the tunnel terminal.

- [ ] **V4: It survives logging out**
  - **Where:** laptop
  - **Run:** Close every SSH session, then `ssh -i ~/.ssh/isba4775_azure azureuser@$VM_IP 'curl -s http://127.0.0.1:8000/health'`
  - **Why:** Proves the `nohup` start in R1 works.
  - **Check:** It returns the same healthy JSON as V2.
  - **Undo:** Nothing to undo. This step only reads.

## Appendix: Stop the VM when you're done (not one of your sections)

### Task X: Stop the app and deallocate the VM

- [ ] **X1: Stop uvicorn**
  - **Where:** VM
  - **Run:**
    ```bash
    pkill -f 'uvicorn app.main:create_app'
    sleep 2; pgrep -f 'uvicorn app.main:create_app' || echo stopped
    sqlite3 -readonly ~/career-platform-data/career_platform.db "PRAGMA integrity_check;"
    ```
  - **Why:** Closes the app's DB connections cleanly before the power goes off.
  - **Check:** It prints `stopped`, then `ok`.
  - **Undo:** Run R1 again.

- [ ] **X2: Deallocate the VM**
  - **Where:** laptop (`az` is installed), or portal (you click: Overview → **Stop**)
  - **Run:** `az vm deallocate -g rg-career-platform -n vm-career-platform`. Never use `sudo shutdown` inside the VM. That leaves it "Stopped", and a stopped VM still bills for compute.
  - **Why:** Deallocating ends compute billing. The disk, with the clone, `.env` and DB on it, is kept (storage is still billed, at a small cost).
  - **Check:** This must print exactly `VM deallocated`:
    ```bash
    az vm get-instance-view -g rg-career-platform -n vm-career-platform \
      --query "instanceView.statuses[?starts_with(code,'PowerState/')].displayStatus" -o tsv
    ```
  - **Undo:** `az vm start -g rg-career-platform -n vm-career-platform`, then redo S1 (the IP may change), S3 and R1, and check with V1–V2.

## Full rollback (reverse order)

The Codespace still has the original code and DB. Your laptop DB and GitHub are never modified either, so rollback only removes what was added to the VM and to `/tmp` on the laptop.

0. If the VM is deallocated, start it (X2 Undo) and redo S1.
1. VM: `pkill -f 'uvicorn app.main:create_app'; rm -f ~/uvicorn.pid ~/uvicorn.log`
2. VM: `rm -rf ~/career-platform-data`
3. VM: `rm -rf ~/career-platform-2-`
4. VM: uninstall uv (P1 Undo)
5. VM: remove the apt packages that weren't preinstalled (K2 Undo), then `rm ~/preinstalled-packages.txt`
6. Laptop: `rm /tmp/career_platform_upload.db /tmp/laptop_counts.txt /tmp/laptop_dump.sha`
