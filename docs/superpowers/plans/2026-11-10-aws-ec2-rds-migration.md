# Move gavinclarke.me from Railway to AWS (EC2 + RDS)

Written 2026-11-10 at 10:00 PST, on branch `aws-migration`.
**Deadline: live on AWS by 13:45 PST today.**
Status: **draft, not approved.** Nothing in AWS exists yet.

## Where we are

- Railway's trial ended on 2026-11-07. Since then `gavinclarke.me` returns
  Railway's "Application not found" 404. There is no Railway site to fall
  back to, so the switchover happens as soon as the AWS copy passes its
  tests.
- The data to move is `../railway-move/railway-pg-2026-11-03-132243.dump`:
  - Postgres 18.6, revision `d4a8f1c2e7b9`, SHA-256 `7ce0c7d7…`.
  - It passed a restore test on 2026-11-03.
  - No content changed after it.
- The app is FastAPI with Jinja pages and SQLAlchemy. Migrations are
  Alembic, and Python packages are locked in `uv.lock`. It has:
  - no file uploads,
  - no seeding at startup,
  - no email sending.
- DNS is at Cloudflare:
  - `@` is a CNAME to `dwaascah.up.railway.app`, DNS only.
  - `www` is a proxied placeholder that Cloudflare redirects.
  - The Zoho mail records (MX, SPF, DKIM, DMARC, verification) must not
    change.
- The rules come from the course guide (`aws-migration.md` §7–§12) and the
  `ISBA4775EC2Migration` policy:
  - `us-east-1`, `t3.micro` or `t3.small`, IMDSv2 required.
  - A `db.t3.micro` or `db.t4g.micro` database, Single-AZ, 20 GB,
    encrypted and private.

## Your decisions (2026-11-10)

| Decision | Answer |
|---|---|
| Who does the AWS steps | **You, in the AWS console.** I give each screen's choices and why, then check the result with read-only commands |
| Updating the site later | **Manual:** SSH in and run `deploy/deploy.sh` |
| Protecting edits | **RDS automated backups only, kept 7 days, with no manual routine.** Losing up to a day of edits is acceptable. Point-in-time restore usually does better than that. There's **one** export outside AWS, taken right after the switchover, to your **personal** Google Drive (guide §2). The next one comes with the February move |
| Where you connect from | SSH from home only (`99.7.122.53`). On campus, add that address temporarily and remove it afterward |
| When credits run out | At about $26.82/month, the $100 lasts until around 2027-03-03. **Move to a cheaper setup of about $8–10/month by the end of February 2027**, and keep the site up for employers |

## Goals

- **Goal:** the site, with the Nov 3 data, served over HTTPS at
  `gavinclarke.me` from AWS by 13:45.
- **Not today:** automatic deploys, monitoring beyond manual checks, a
  custom VPC, analytics changes.
- **Failure even if the site loads:**
  - `/admin` is reachable,
  - the database is reachable from the internet,
  - the app is running on an empty SQLite file,
  - mail at the domain breaks,
  - a password or key ends up in Git or chat.

## Timeline

| By (PST) | Phase |
|---|---|
| 10:20 | **0** Your prep. **1** Code fixes, done by me at the same time |
| 10:50 | **2** You create the key pair, security groups, subnet group and RDS database in the console |
| 11:15 | **3** You launch the EC2 instance and attach the Elastic IP |
| 12:05 | **4** Server setup, restore and checks, done by me over SSH, with you approving |
| 12:30 | **5** Test on `aws.gavinclarke.me` |
| 12:50 | **6** Switch `gavinclarke.me` over |
| 13:30 | **7** Notes, README and merge |
| 13:45 | Deadline, with 15 minutes of buffer |

**If we're behind at 12:30,** switch over as soon as Phase 5 passes and
finish Phase 7 after the deadline. The site being up matters most.

---

## Phase 0: your prep (10:00–10:20)

Run these yourself with `!`, so passwords and passphrases never pass
through me.

1. **Sign in to the CLI** as `isba-student`, so I can check your work:
   `! aws login --profile isba-4775 --region us-east-1`
2. **SSH key with a passphrase:**
   `! ssh-keygen -t ed25519 -f ~/.ssh/isba4775_aws -C isba4775-aws`
3. **Load the key into the macOS keychain,** so SSH works without me seeing
   the passphrase:
   `! ssh-add --apple-use-keychain ~/.ssh/isba4775_aws`
4. **Generate the database password** into a private file. It's 32 letters
   and digits, so it's safe in a URL:
   `! sh -c 'umask 077; mkdir -p ~/.config/career-platform; LC_ALL=C tr -dc A-Za-z0-9 </dev/urandom | head -c 32 > ~/.config/career-platform/aws-db-password'`
5. **Zero-spend budget,** if you haven't made one (guide §1). Sign in as
   **root**, open Billing → Budgets → Create budget → Zero spend budget.
   Then sign out of root and back in as `isba-student`.

## Phase 1: code fixes (me, 10:00–10:20, test first)

1. **Close `/admin` by default.** Change `environment`'s default in
   `app/config.py` from `development` to `production`. Your local `.env`
   already sets `development`. Test: with no `ENVIRONMENT` set and no
   Railway variables, `/admin` returns 404.
2. **Refuse to start on SQLite in production.** If `environment` isn't
   `development` and `DATABASE_URL` is SQLite, the app fails at startup.
   Test both cases. This closes the trap where an empty SQLite file looks
   healthy.
3. **`/health` reports the commit off Railway.** Read `GIT_COMMIT_SHA`,
   falling back to `RAILWAY_GIT_COMMIT_SHA`, with a test.
4. **Privacy page:** `templates/privacy.html:27` says the site runs on
   Railway. I'll draft new wording about AWS and nginx logs for you to
   approve.
5. **Scripts and config:**
   - `deploy/deploy.sh` runs on the server: pull, `uv sync --frozen
     --no-dev`, `alembic upgrade head`, record the commit, restart, and
     check `/health`.
   - Config files for systemd and nginx.
6. Run the full test suite and commit to `aws-migration`.

## Phase 2: security and database (you, in the console, 10:20–10:50)

Before starting, make sure the region at the top right is **N. Virginia
(us-east-1)**. Tag everything with `Project = career-platform`.

**2a. Import the key pair:** EC2 → Key Pairs → Actions → **Import key pair**.
- Name: `isba4775-aws`
- Paste the contents of `~/.ssh/isba4775_aws.pub`. Copy it with
  `! pbcopy < ~/.ssh/isba4775_aws.pub`.
- Only the public half goes to AWS. The policy blocks "Create key pair" on
  purpose.

**2b. Web security group:** EC2 → Security Groups → **Create security group**.
- Name `career-platform-web`, in the default VPC.
- Inbound rules:
  - SSH (22) from **My IP**. It should show `99.7.122.53/32`.
  - HTTP (80) from Anywhere-IPv4.
  - HTTPS (443) from Anywhere-IPv4.
- Leave outbound at the default (all).

**2c. Database security group:** create another.
- Name `career-platform-db`, in the default VPC.
- Inbound: **PostgreSQL (5432)**, with the source set to the security
  group `career-platform-web`, not an IP address.
- This is what keeps the database reachable only from your server.

**2d. Subnet group:** RDS → Subnet groups → **Create DB subnet group**.
- Name `career-platform-db-subnets`, in the default VPC.
- Add all six us-east-1 zones and their subnets.
- Why: a database created on the `default` group can be made public by
  default.

**2e. Database:** RDS → Databases → **Create database** → Full configuration
(Standard create).

| Section | Choose |
|---|---|
| Engine | PostgreSQL, version **18.6** |
| Template | **Free tier** if shown, otherwise Dev/Test |
| Availability | **Single-AZ** |
| Identifier | `career-platform-db` |
| Master username | `career_admin` |
| Credentials | **Self managed**. Paste the password with `! pbcopy < ~/.config/career-platform/aws-db-password`, then clear the clipboard afterward |
| Instance class | Burstable → **db.t4g.micro** |
| Storage | gp3, **20 GiB**, **storage autoscaling off** |
| Compute resource | **Don't connect to an EC2 compute resource**. That option creates its own security groups |
| VPC and subnet group | Default VPC, `career-platform-db-subnets` |
| Public access | **No** |
| Security group | Existing **`career-platform-db`** only. Remove `default` |
| Monitoring | **Turn off Enhanced Monitoring**. It needs an IAM role the policy can't create, so leaving it on makes creation fail |
| Initial database name (Additional configuration) | `career_platform` |
| Backups | On, retention **7 days** |
| Encryption | On, default key `aws/rds` |
| Log exports | None |
| Minor version upgrade | On. Maintenance window Mon 11:00 UTC (3:00 Pacific) |
| Deletion protection | **On** |

Choose **Create database**. It takes 5 to 10 minutes, so move to Phase 3
while it builds.

**My check:** a read-only `describe` confirms:
- PubliclyAccessible = false
- StorageEncrypted = true
- MultiAZ = false
- the security group is `career-platform-db` only
- BackupRetentionPeriod = 7
- DeletionProtection = true

## Phase 3: server (you, in the console, 10:50–11:15)

**3a.** EC2 → Instances → **Launch instance**.

| Section | Choose |
|---|---|
| Name | `career-platform-web` |
| Image | **Ubuntu Server 26.04 LTS** by Canonical, **64-bit (x86)**. Not "Pro". I'll confirm the AMI ID |
| Instance type | **t3.micro** |
| Key pair | `isba4775-aws` |
| Network | Default VPC, any subnet, **auto-assign public IP: Enable**, existing security group **`career-platform-web`** |
| Storage | **20 GiB gp3**, **Encrypted** (under Advanced, default key) |
| Advanced: Credit specification | **Standard** |
| Advanced: Metadata version | **V2 only (token required)**. Without it the policy blocks the launch |
| Advanced: IAM instance profile | None |

**3b. Elastic IP:** EC2 → Elastic IPs → **Allocate**, then **Associate** it
with `career-platform-web`. It's the fixed address DNS will point at. It
bills while idle, so release it if the instance is ever terminated.

**My check:**
- `describe` confirms the type, IMDSv2, Standard credits, encrypted
  storage, the security group and the Elastic IP.
- I compare the SSH host key fingerprint against the instance's
  **console output** before the first connection.

If a launch is refused, I decode the error to see which policy rule fired.

## Phase 4: server setup, restore and checks (me over SSH, 11:15–12:05)

You approve each command. Nothing touches the AWS console.

1. **Packages:**
   - `apt` upgrade, plus `nginx`, `certbot`, `python3-certbot-nginx`,
     `postgresql-client-18`, `git`.
   - `uv`, which installs the Python 3.12 named in `.python-version`.
   - Unattended security upgrades stay on.
2. **Code:**
   - `git clone` the public repo into `/home/ubuntu/career-platform`.
   - Check out `aws-migration`.
   - `uv sync --frozen --no-dev`.
3. **Secrets:** `/etc/career-platform.env`, owned by `root:ubuntu`, mode
   640, never in Git.
   - `DATABASE_URL=postgresql://career_admin:<password>@<endpoint>:5432/career_platform?sslmode=require`
   - `ENVIRONMENT=production`
   - `GA_MEASUREMENT_ID=<same as Railway>`
   - `GIT_COMMIT_SHA`
   - The password goes from your local file to the server over SSH and is
     never printed.
4. **Restore:**
   1. `scp` the dump to the server and check its SHA-256.
   2. Run `pg_restore --no-owner --no-acl --exit-on-error` into the empty
      database.
   3. **Then** run `alembic upgrade head`, which should report no change at
      `d4a8f1c2e7b9`.
   - Never run seed scripts or the Azure deploy script.
   - Compare all 10 tables' row counts and content fingerprints with the
     Nov 3 values.
   - Delete the dump from the server afterward.
5. **systemd service `career-platform`:**
   - Runs as `ubuntu`, using `EnvironmentFile=/etc/career-platform.env`.
   - uvicorn on **127.0.0.1:8000**, 2 workers, `--proxy-headers
     --forwarded-allow-ips=127.0.0.1`.
   - `Restart=always`, enabled at boot.
6. **nginx:**
   - `server_name gavinclarke.me aws.gavinclarke.me` proxies to
     `127.0.0.1:8000` and sends `X-Forwarded-Proto`.
   - `location /admin { return 404; }`.
   - A default server returns 444 to the bare IP and other names.
   - `aws.gavinclarke.me` responses carry `X-Robots-Tag: noindex`.
   - The welcome page is removed.
7. **Checks:**
   - Through nginx, `/health` shows `"fallback": false` and the commit.
   - All 4 project pages render, and `/admin` returns 404.
   - The app comes back after `sudo reboot`.
   - Your laptop can't reach port 8000 or the database endpoint.

## Phase 5: test on aws.gavinclarke.me (12:05–12:30)

1. I add a Cloudflare record: **A `aws` → Elastic IP, DNS only.** It's a
   new record, and nothing else changes. You confirm the grey cloud in the
   Cloudflare dashboard and run `! nslookup aws.gavinclarke.me`.
2. I run `certbot --nginx -d aws.gavinclarke.me` and turn on the HTTP→HTTPS
   redirect.
3. Together we check:
   - The padlock, in your browser.
   - `/`, `/resume`, `/projects`, the 4 project pages, `/contact` and
     `/privacy` return 200 with projects showing.
   - `/admin` and an unknown project URL return 404.
   - The `noindex` header is present.
   - The RDS console shows **Publicly accessible: No**.

## Phase 6: switch gavinclarke.me over (12:30–12:50)

1. Back up the DNS records to a local file first.
2. I replace **only `@`**: delete the CNAME to Railway, then add an
   **A record to the Elastic IP, DNS only**.
   - **MX, SPF, DKIM, DMARC, Zoho verification and `www` stay as they
     are.**
   - You confirm in the dashboard.
3. Once `dig gavinclarke.me` returns the Elastic IP, I run
   `certbot --nginx --expand -d aws.gavinclarke.me -d gavinclarke.me`. The
   site is already down, so a minute without HTTPS isn't a new outage.
4. Repeat the Phase 5 checks on `gavinclarke.me`, plus:
   - `www` redirects.
   - `sudo certbot renew --dry-run` passes.
   - A test email to your domain address arrives.
5. **The one outside export:**
   1. Take a `pg_dump -Fc` of RDS through an SSH tunnel, using the
      Postgres 18 client on your laptop.
   2. Check its SHA-256 and confirm its row counts match the Nov 3 values.
   3. You upload it to your **personal** Google Drive.

**If something breaks after this point,** we fix it forward. There's no
Railway to go back to. The data is protected by RDS point-in-time restore
and the dumps.

## Phase 7: record and tidy (12:50–13:30)

- `docs/migration-notes.md`: each step, deviations from this plan, the
  check evidence, anything unverified, and cost (about $26/month on
  credits).
- README:
  - The new architecture, with a Mermaid diagram: Cloudflare DNS → nginx
    on EC2 (HTTPS ends here) → app → private RDS with its backups. SSH is
    the only admin path, and Railway is marked as ended.
  - How to deploy, back up, restore and edit content.
  - What was tested.
  - Next steps, including the cheaper setup in March.
- Remove `railway.json` and its tests.
- Merge `aws-migration` into `main`. The server then runs `main`
  (`deploy/deploy.sh` switches it).

## How you'll work after today

- **Deploy a change:** merge to `main`, then
  `ssh ubuntu@<elastic-ip> ~/career-platform/deploy/deploy.sh`.
- **Edit content:**
  1. Open an SSH tunnel to RDS:
     `ssh -L 15433:<rds-endpoint>:5432 ubuntu@<elastic-ip>`.
  2. Run the app locally with `ENVIRONMENT=development` and `DATABASE_URL`
     pointing at the tunnel, and use `/admin` there.
  3. RDS's daily automated backup covers the change. There's no manual
     step.
- **On campus:**
  1. EC2 → Security Groups → `career-platform-web` → Edit inbound rules.
  2. Add SSH from **My IP** with the description `campus, temporary`.
  3. Do the work.
  4. Delete that rule before you leave.
- **Restore after a bad edit:** RDS → Databases → `career-platform-db` →
  Actions → **Restore to point in time**. It restores into a new database,
  which you then point `DATABASE_URL` at.

## Calls I made (correct any that are wrong)

- **Database user:** the app uses the RDS master user `career_admin`, as the
  guide does. A separate app user with fewer rights is a later improvement.
- **Database class:** `db.t4g.micro` rather than `db.t3.micro`. Both are
  allowed; the t4g is the newer and cheaper one.
- **Analytics on the test site:** left on, to save time. Your few test visits
  will appear in GA.
- **DNS and server commands:** I run them, with your approval each time. Your
  "learn the screens" choice covers the AWS console. Say so if you want to
  make the Cloudflare changes in its dashboard too.
- **No `www` change:** Cloudflare's redirect from `www` to the bare domain
  keeps working, because it doesn't depend on where the bare domain points.

## Open risks

- **Policy gaps:** the deny rule for making a database public probably
  doesn't apply to changes after creation, so never change that setting.
- **One server:** if the instance fails, the site is down until it's
  rebuilt from this plan, which takes about an hour. The data is safe in RDS.
- **Backups live inside the AWS account:** RDS automated backups are
  deleted along with the database, and lost if the account closes. Before
  deleting anything in February, take a fresh export outside AWS first.
- **Expiring CLI session:** the `aws login` session lasts up to 12 hours;
  run it again if checks start failing.
