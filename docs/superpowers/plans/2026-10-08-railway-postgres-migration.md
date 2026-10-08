# Railway + PostgreSQL Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Serve gavinclarke.me from the Railway `web` service backed by Railway Postgres, with the same content and fallback behavior as the Azure VM, then retire the VM as the live host.

**Architecture:** The app stays one FastAPI process; only its database URL changes. Code tasks (1–6) make the app Postgres-capable while every test still runs on SQLite, and optionally on a local Postgres. Each deploy runs only `alembic upgrade head`, which builds the schema and never inserts content. The content arrives once: a one-off copy moves the VM's current rows into Postgres. Then a DNS switch moves the domain. The VM keeps running untouched until the domain is verified on Railway, so rollback is a DNS change.

**Tech Stack:** FastAPI, SQLAlchemy 2.1, Alembic 1.20, psycopg 3 (`psycopg[binary]`), uv, Railway (Railpack builder), PostgreSQL, pytest.

**Spec:** Your request of 2026-10-08 (no separate spec). Builds on `docs/superpowers/plans/2026-10-01-operate-the-vm.md` (the current VM setup) and `PRODUCT.md` (fallback is a hard requirement).

## Where things stand (inspected 2026-10-08)

| Item | Value |
|---|---|
| Railway project | `renewed-strength` (`6d7a9dc0-193f-4901-9c99-b351d216935d`), environment `production`, linked to this folder |
| Railway services | `Postgres` (deployed, empty database), `web` (empty: no source, no variables, never deployed) |
| Postgres public access | **Off.** Its variables include `DATABASE_URL` (private `*.railway.internal` host) but no `DATABASE_PUBLIC_URL`. Your laptop cannot reach it until Task 7 enables the TCP proxy |
| Live site | `https://gavinclarke.me` → A record `20.114.0.108` (Azure VM, nginx + Certbot, commit `a417756`) |
| Content | Source of truth: the VM's `~/career-platform-data/career_platform.db`, schema `d4a8f1c2e7b9`. The laptop copy currently has the same bytes, but Task 7 copies from a fresh VM snapshot, not the laptop. 19 rows: profiles 1, experiences 3, projects 3, skills 7, education 1, certifications 0, links 0, site_meta 2, volunteer_work 2. Every string is well under its `String(n)` limit, which Postgres enforces and SQLite does not |
| Local tools | `uv` 0.12, Railway CLI 5.64 (logged in). No Docker, no local Postgres, no `psql` |
| Seeding | None in the deploy path. `app/seed_data.py` defines `seed_database()`, but nothing calls it: not app startup, not any migration (none write data), not the deploy commands. Task 6 adds a test that keeps it that way |
| Uncommitted | `app/config.py`: `railway_database_url: str \| None = None`, so the `RAILWAY_DATABASE_URL` line in `.env` doesn't stop the app loading. That URL uses the private host, so nothing in this plan uses it |

### What breaks today if you just point the app at Postgres

1. **No driver.** Neither `pyproject.toml`/`uv.lock` (which Railpack installs from) nor `requirements.txt` includes a Postgres driver.
2. **URL scheme.** Railway's `postgresql://…` makes SQLAlchemy look for `psycopg2`. psycopg 3 needs `postgresql+psycopg://…`.
3. **Alembic ignores the app's settings.** `migrations/env.py` reads `sqlalchemy.url` from `alembic.ini`, which is hardcoded to `sqlite:///./career_platform.db`. A migration on Railway would create tables in a throwaway SQLite file and leave Postgres empty.
4. **`/admin` becomes public.** Only nginx on the VM blocks it (`location /admin { return 404; }`). On Railway, `GET /admin` would expose the admin payload, and `PUT /admin/profile` would let anyone rewrite the in-memory fallback profile.
5. **Outages hang instead of falling back.** There's no connect timeout. With an unreachable Postgres, each read waits for the OS TCP timeout, so pages hang for minutes before the fallback renders.

## Global Constraints

- Railway project `renewed-strength`, environment `production`, services named exactly `Postgres` and `web`.
- Driver: psycopg 3, installed as `psycopg[binary]>=3.2`; SQLAlchemy URL scheme `postgresql+psycopg://`.
- The database password never appears in Git, chat, or command output. The `web` service gets it through the reference `${{Postgres.DATABASE_URL}}`, and laptop commands get it through `railway run`'s environment injection. Never `echo` or print a URL that contains it.
- Code tasks 1–6 happen on branch `feat/railway-postgres` and merge through a PR *before* Task 7. Once the `web` service is connected to the repo, every push to `main` deploys.
- Every test passes on SQLite (the default), and on Postgres when `TEST_DATABASE_URL` is set (Task 4).
- `ENVIRONMENT=production` on Railway. In production the app does not serve `/admin` at all.
- The app sits behind Railway's proxy, which terminates HTTPS and forwards plain HTTP with `X-Forwarded-Proto: https`. Uvicorn must trust that header (`--forwarded-allow-ips="*"`), or the app builds `http://` URLs (redirects, and any `url_for` asset links), which browsers block or downgrade on an HTTPS page.
- Fallback stays a hard requirement: with Postgres down, every public page still renders the real profile, in under 10 seconds.
- The VM stays running and unchanged until Task 8's checks pass and 7 days have gone by. Don't stop its services, and don't edit its database.
- The rows in Railway Postgres come from the VM's database, copied once in Task 7. Seeding stays out of deploy: no build, pre-deploy, start or migration step may call `seed_database()` or insert content. The deploy builds the schema only.
- Content freeze: no edits to the laptop SQLite or the VM database between Task 7's copy and the end of Task 8. If one is unavoidable, rerun the copy into a fresh Postgres.

## Review Focus

1. **Postgres unreachable at request time.** Expect pages to render the fallback profile in under 10 s, not hang. Pinned in Task 1 (`test_pages_fall_back_quickly_when_postgres_is_unreachable`).
2. **Copy script run twice, or into a database that already has content.** Expect it to refuse and change nothing, never to duplicate rows. Pinned in Task 5 (`test_copy_refuses_non_empty_target_and_changes_nothing`).
3. **A new row added after the copy, without an explicit id** (e.g. a fourth project). Expect it to get the next free id, not a duplicate-key error from a Postgres sequence still at 1. Pinned in Task 5 (`test_new_rows_after_copy_get_fresh_ids`), meaningful on Postgres.
4. **`/admin` and `PUT /admin/profile` in production.** Expect a plain 404, with nothing exposed or changed. Pinned in Task 3.
5. **`DATABASE_URL` in the older `postgres://` form,** which some tools and providers still emit. Expect it to work the same as `postgresql://`. Pinned in Task 1 (`test_normalize_database_url`).

---

## File map

| File | Responsibility | Task |
|---|---|---|
| `pyproject.toml`, `uv.lock`, `requirements.txt` | Add `psycopg[binary]` | 1 |
| `app/config.py` | `normalize_database_url()`; settings apply it | 1 |
| `app/db.py` | `engine_options()`: SQLite thread flag, Postgres connect timeout + pre-ping | 1 |
| `tests/test_database_config.py` | URL, engine options, fast-fallback tests | 1 |
| `migrations/env.py`, `alembic.ini` | Alembic uses `settings.database_url` | 2 |
| `tests/test_migrations.py` | Alembic migrates the database named by `DATABASE_URL` | 2 |
| `app/main.py` | Mount the admin router only outside production | 3 |
| `tests/test_admin_routes.py` | Production hides `/admin` | 3 |
| `tests/conftest.py` | Optional Postgres test database via `TEST_DATABASE_URL` | 4 |
| `app/content_copy.py` | `copy_content()` + CLI: copy every content table, reset sequences, verify counts | 5 |
| `tests/test_content_copy.py` | Copy, refusal, fresh-id tests | 5 |
| `railway.json`, `.python-version` | Build, pre-deploy migration (no seed), start command, health check | 6 |
| `tests/test_deploy_config.py` | Deploy commands never seed; serving never writes content | 6 |
| Railway (CLI/dashboard), DNS | Variables, first deploy, data copy, domain cutover | 7–8 |

---

### Task 1: Postgres driver, URL normalization, fast-failing connections

**Files:**
- Modify: `pyproject.toml`, `uv.lock` (via `uv add`), `requirements.txt`
- Modify: `app/config.py`
- Modify: `app/db.py`
- Create: `tests/test_database_config.py`

**Interfaces:**
- Produces: `app.config.normalize_database_url(url: str) -> str`; `app.db.engine_options(url: str) -> dict[str, object]`. `settings.database_url` is always normalized. Tasks 4 and 5 use both.

- [ ] **Step 0: Branch and commit the pending settings field**

```bash
git switch main && git pull --ff-only
git switch -c feat/railway-postgres
git add app/config.py
git commit -m "fix: accept RAILWAY_DATABASE_URL in .env without failing settings validation"
```

- [ ] **Step 1: Write the failing tests**

Create `tests/test_database_config.py`:

```python
import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import normalize_database_url
from app.db import engine_options
from app.main import create_app


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        ("postgresql://u:p@host:5432/db", "postgresql+psycopg://u:p@host:5432/db"),
        ("postgres://u:p@host:5432/db", "postgresql+psycopg://u:p@host:5432/db"),
        ("postgresql+psycopg://u:p@host/db", "postgresql+psycopg://u:p@host/db"),
        ("sqlite:///./career_platform.db", "sqlite:///./career_platform.db"),
    ],
)
def test_normalize_database_url(given, expected):
    assert normalize_database_url(given) == expected


def test_engine_options_for_sqlite_allow_cross_thread_use():
    assert engine_options("sqlite:///./x.db") == {"connect_args": {"check_same_thread": False}}


def test_engine_options_for_postgres_fail_fast_and_ping():
    options = engine_options("postgresql+psycopg://u:p@host/db")
    assert options["connect_args"] == {"connect_timeout": 2}
    assert options["pool_pre_ping"] is True


def test_pages_fall_back_quickly_when_postgres_is_unreachable(monkeypatch):
    # 10.255.255.1 is non-routable: connections hang rather than being refused,
    # which is what a dead database looks like from the app.
    url = "postgresql+psycopg://user:pass@10.255.255.1:5432/db"
    engine = create_engine(url, **engine_options(url))
    monkeypatch.setattr("app.db.SessionLocal", sessionmaker(bind=engine))
    monkeypatch.setattr("app.main.engine", engine)

    started = time.monotonic()
    response = TestClient(create_app()).get("/")
    elapsed = time.monotonic() - started

    assert response.status_code == 200
    assert "Gavin Clarke" in response.text
    assert elapsed < 10
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_database_config.py -v`
Expected: collection error, `ImportError: cannot import name 'normalize_database_url' from 'app.config'`.

- [ ] **Step 3: Add the driver**

```bash
uv add 'psycopg[binary]>=3.2'
echo 'psycopg[binary]>=3.2' >> requirements.txt
uv sync
```

Expected: `pyproject.toml` lists `"psycopg[binary]>=3.2"`, `uv.lock` gains `psycopg` and `psycopg-binary`, and `.venv/bin/python -c "import psycopg; print(psycopg.__version__)"` prints a 3.x version.

- [ ] **Step 4: Normalize the URL in settings**

Replace `app/config.py` with:

```python
from pydantic import ConfigDict, field_validator
from pydantic_settings import BaseSettings


def normalize_database_url(url: str) -> str:
    """Point bare Postgres URLs (the form Railway provides) at the psycopg 3 driver."""
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env")

    app_name: str = "Career Platform"
    database_url: str = "sqlite:///./career_platform.db"
    railway_database_url: str | None = None
    environment: str = "development"

    @field_validator("database_url")
    @classmethod
    def _use_psycopg_driver(cls, value: str) -> str:
        return normalize_database_url(value)


settings = Settings()
```

- [ ] **Step 5: Fail fast on Postgres connections**

Replace the engine lines in `app/db.py` (currently lines 8–9: `connect_args = …` and `engine = create_engine(…)`) with:

```python
def engine_options(url: str) -> dict[str, object]:
    if url.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}
    # A short connect timeout lets the fallback content render quickly when Postgres is down.
    # Each page makes several reads, so this bounds a full outage to a few seconds per page.
    return {"connect_args": {"connect_timeout": 2}, "pool_pre_ping": True}


engine = create_engine(settings.database_url, **engine_options(settings.database_url))
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_database_config.py -v`
Expected: 7 passed. The fallback test takes roughly 2–8 s, depending on whether later reads in the request retry the connection (2 s each) or fail at once on the session's failed state. Either way the page must render the fallback.

If the fallback test takes more than 10 s, count the reads made per request on `/` (profile, site meta, projects) and make sure each is wrapped by `DatabaseUnavailableError` handling. Don't raise the timeout.

- [ ] **Step 7: Run the whole suite**

Run: `.venv/bin/python -m pytest -q`
Expected: 28 passed (the 21 existing plus 7 new).

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml uv.lock requirements.txt app/config.py app/db.py tests/test_database_config.py
git commit -m "feat: support Postgres via psycopg with fast-failing connections"
```

---

### Task 2: Alembic migrates the database the app uses

**Files:**
- Modify: `migrations/env.py:13-16`
- Modify: `alembic.ini:3`
- Create: `tests/test_migrations.py`

**Interfaces:**
- Consumes: `app.config.settings.database_url` (normalized, Task 1).
- Produces: `alembic upgrade head` targets whatever `DATABASE_URL` (env var or `.env`) names. Task 6's pre-deploy command relies on this.

- [ ] **Step 1: Write the failing test**

Create `tests/test_migrations.py`:

```python
import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect, text

ROOT = Path(__file__).resolve().parents[1]


def test_alembic_upgrades_the_database_named_by_database_url(tmp_path):
    target = tmp_path / "migrated.db"
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{target}"}

    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=ROOT, env=env, capture_output=True, text=True,
    )

    assert result.returncode == 0, result.stderr
    engine = create_engine(f"sqlite:///{target}")
    assert {"profiles", "projects", "site_meta", "volunteer_work"} <= set(inspect(engine).get_table_names())
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "d4a8f1c2e7b9"
```

- [ ] **Step 2: Run it to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_migrations.py -v`
Expected: FAIL. `migrated.db` has no tables, because Alembic upgraded `./career_platform.db` (already at head, so nothing changed there).

- [ ] **Step 3: Make Alembic read the app's settings**

In `migrations/env.py`, replace:

```python
from app.models import Base

config = context.config
```

with:

```python
from app.config import settings
from app.models import Base

config = context.config
# The app's settings (env var, then .env) decide which database to migrate, never alembic.ini.
# "%" is doubled because Alembic's config parser treats it as interpolation.
config.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))
```

In `alembic.ini`, replace line 3 (`sqlalchemy.url = sqlite:///./career_platform.db`) with:

```ini
# Set at runtime from DATABASE_URL by migrations/env.py.
sqlalchemy.url =
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_migrations.py -v`
Expected: PASS.

- [ ] **Step 5: Check the local database is still current**

Run: `.venv/bin/python -m alembic current`
Expected: `d4a8f1c2e7b9 (head)` (read from `./career_platform.db` via `.env`).

- [ ] **Step 6: Run the whole suite and commit**

Run: `.venv/bin/python -m pytest -q` (expected: 29 passed)

```bash
git add migrations/env.py alembic.ini tests/test_migrations.py
git commit -m "fix: run Alembic against the app's DATABASE_URL instead of a hardcoded SQLite file"
```

---

### Task 3: No `/admin` in production

**Files:**
- Modify: `app/main.py` (the `app.include_router(admin_router)` line)
- Modify: `tests/test_admin_routes.py`

**Interfaces:**
- Consumes: `app.config.settings.environment`.
- Produces: with `ENVIRONMENT=production`, no `/admin` routes exist (JSON 404, from the handler added in commit `a417756`).

- [ ] **Step 1: Write the failing test**

Append to `tests/test_admin_routes.py`:

```python
def test_admin_routes_do_not_exist_in_production(monkeypatch):
    monkeypatch.setattr("app.main.settings.environment", "production")
    client = TestClient(create_app())

    assert client.get("/admin").status_code == 404
    response = client.put(
        "/admin/profile",
        json={"full_name": "Intruder", "headline": "x", "summary": "x", "email": "x@example.com"},
    )
    assert response.status_code == 404
    assert "Intruder" not in client.get("/").text
```

- [ ] **Step 2: Run it to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_admin_routes.py -v`
Expected: `test_admin_routes_do_not_exist_in_production` FAILS (`/admin` returns 200).

- [ ] **Step 3: Mount the admin router only outside production**

In `app/main.py`, replace `    app.include_router(admin_router)` with:

```python
    # On the VM, nginx hid /admin. Railway has no such layer, so production doesn't mount it.
    if settings.environment != "production":
        app.include_router(admin_router)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_admin_routes.py -v`
Expected: 3 passed. The existing admin tests still pass because the default environment is `development`.

- [ ] **Step 5: Run the whole suite and commit**

Run: `.venv/bin/python -m pytest -q` (expected: 30 passed)

```bash
git add app/main.py tests/test_admin_routes.py
git commit -m "fix: don't serve /admin when ENVIRONMENT=production"
```

---

### Task 4: Run the test suite against a real Postgres

SQLite accepts things Postgres rejects: over-length strings, integer sequences you never reset. This task lets the whole suite run on Postgres with one environment variable.

**Files:**
- Modify: `tests/conftest.py` (the `db_engine` fixture)

**Interfaces:**
- Consumes: `normalize_database_url`, `engine_options` (Task 1).
- Produces: when `TEST_DATABASE_URL` is set, every test's `db_engine` is a freshly emptied Postgres database. Otherwise it's a temp SQLite file, as now.

- [ ] **Step 1: Install a local Postgres for tests**

```bash
brew install postgresql@17
brew services start postgresql@17
"$(brew --prefix postgresql@17)/bin/createdb" career_test
```

Expected: `brew services list` shows `postgresql@17 started`, and `createdb` prints nothing.

This is a local, throwaway test database. Never point `TEST_DATABASE_URL` at Railway: the fixture drops every table.

- [ ] **Step 2: Make `db_engine` switchable**

In `tests/conftest.py`, add `import os` at the top, extend the imports to:

```python
from app.config import normalize_database_url
from app.db import engine_options
```

and replace the `db_engine` fixture with:

```python
@pytest.fixture
def db_engine(tmp_path):
    test_url = os.environ.get("TEST_DATABASE_URL")
    if test_url:
        # Local throwaway Postgres only: every table is dropped before and after each test.
        url = normalize_database_url(test_url)
        engine = create_engine(url, **engine_options(url))
        Base.metadata.drop_all(engine)
    else:
        engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False})
    yield engine
    if test_url:
        Base.metadata.drop_all(engine)
    engine.dispose()
```

- [ ] **Step 3: Run the suite on SQLite (unchanged behavior)**

Run: `.venv/bin/python -m pytest -q`
Expected: 30 passed.

- [ ] **Step 4: Run the suite on Postgres**

Run: `TEST_DATABASE_URL=postgresql://localhost/career_test .venv/bin/python -m pytest -q`
Expected: 30 passed.

`test_alembic_upgrades_the_database_named_by_database_url` still uses its own SQLite file, which is fine. Any other failure is a real SQLite/Postgres difference: fix the code, not the test.

- [ ] **Step 5: Commit**

```bash
git add tests/conftest.py
git commit -m "test: run the suite against Postgres when TEST_DATABASE_URL is set"
```

---

### Task 5: Content copy script (SQLite → Postgres)

**Files:**
- Create: `app/content_copy.py`
- Create: `tests/test_content_copy.py`

**Interfaces:**
- Consumes: `normalize_database_url`, `engine_options` (Task 1), `app.models.Base`.
- Produces:
  - `copy_content(source: Engine, target: Engine) -> dict[str, int]` (rows copied per table) and `TargetNotEmptyError`.
  - CLI: `python -m app.content_copy SOURCE_URL`, which reads the target URL from the env var `TARGET_DATABASE_URL`, or the one named by `--target-env`. Exit codes: 0 copied, 1 target not empty, 2 target URL missing. Task 7 runs it.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_content_copy.py`:

```python
import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.content_copy import TargetNotEmptyError, copy_content, main
from app.models import Base, Profile, Project, SiteMeta, Skill


@pytest.fixture
def source(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'source.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all(
            [
                Profile(id=1, full_name="Gavin Clarke", headline="Analyst", summary="Summary."),
                Project(id=1, title="One", slug="one", short_summary="First."),
                Project(id=3, title="Three", slug="three", short_summary="Third.", category="Finance"),
                Skill(id=1, name="Excel", category="Technical"),
                SiteMeta(id=1, key="availability", value="Open to roles."),
            ]
        )
        db.commit()
    yield engine
    engine.dispose()


def count(engine, model):
    with Session(engine) as db:
        return db.scalar(select(func.count()).select_from(model))


def test_copy_moves_every_row_with_ids_and_values(source, db_engine):
    counts = copy_content(source, db_engine)

    assert counts["profiles"] == 1 and counts["projects"] == 2 and counts["skills"] == 1
    assert counts["volunteer_work"] == 0
    with Session(db_engine) as db:
        three = db.get(Project, 3)
        assert three.slug == "three" and three.category == "Finance"
        assert db.get(SiteMeta, 1).value == "Open to roles."


def test_copy_refuses_non_empty_target_and_changes_nothing(source, db_engine):
    copy_content(source, db_engine)

    with pytest.raises(TargetNotEmptyError, match="profiles"):
        copy_content(source, db_engine)

    assert count(db_engine, Project) == 2
    assert count(db_engine, Profile) == 1


def test_new_rows_after_copy_get_fresh_ids(source, db_engine):
    copy_content(source, db_engine)

    with Session(db_engine) as db:
        db.add(Project(title="Four", slug="four", short_summary="Added later."))
        db.commit()
        assert db.scalar(select(Project.id).where(Project.slug == "four")) > 3


def test_cli_without_target_url_exits_2(source, monkeypatch, capsys):
    monkeypatch.delenv("TARGET_DATABASE_URL", raising=False)
    assert main([str(source.url)]) == 2
    assert "TARGET_DATABASE_URL" in capsys.readouterr().err


def test_cli_copies_and_prints_counts_without_the_url(source, db_engine, monkeypatch, capsys):
    monkeypatch.setenv("TARGET_DATABASE_URL", db_engine.url.render_as_string(hide_password=False))
    assert main([str(source.url)]) == 0
    output = capsys.readouterr().out
    assert "projects: 2" in output
    assert str(db_engine.url.password or "no-password") not in output
```

- [ ] **Step 2: Run them to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_content_copy.py -v`
Expected: collection error, `ModuleNotFoundError: No module named 'app.content_copy'`.

- [ ] **Step 3: Write the copy module**

Create `app/content_copy.py`:

```python
"""Copy every content table from one database into an empty, migrated one.

Used once to move the SQLite content into Railway Postgres:

    TARGET_DATABASE_URL=... python -m app.content_copy sqlite:///./career_platform.db

The target URL comes from an environment variable so its password never lands in
shell history or output.
"""

import argparse
import os
import sys

from sqlalchemy import create_engine, func, insert, select, text
from sqlalchemy.engine import Engine

from app.config import normalize_database_url
from app.db import engine_options
from app.models import Base


class TargetNotEmptyError(RuntimeError):
    """Raised when the target already holds content, so a copy would duplicate it."""


def copy_content(source: Engine, target: Engine) -> dict[str, int]:
    tables = Base.metadata.sorted_tables

    with target.connect() as connection:
        occupied = [t.name for t in tables if connection.scalar(select(func.count()).select_from(t))]
    if occupied:
        raise TargetNotEmptyError(f"Target already has rows in: {', '.join(occupied)}")

    counts: dict[str, int] = {}
    with source.connect() as reader, target.begin() as writer:
        for table in tables:
            rows = [dict(row._mapping) for row in reader.execute(select(table))]
            if rows:
                writer.execute(insert(table), rows)
            counts[table.name] = len(rows)
            if target.dialect.name == "postgresql":
                # Explicit ids don't advance Postgres sequences; move each past the copied max.
                writer.execute(
                    text(
                        f"SELECT setval(pg_get_serial_sequence('{table.name}', 'id'), "
                        f"COALESCE((SELECT MAX(id) FROM {table.name}), 0) + 1, false)"
                    )
                )

    with target.connect() as connection:
        for table in tables:
            copied = connection.scalar(select(func.count()).select_from(table))
            if copied != counts[table.name]:
                raise RuntimeError(f"{table.name}: expected {counts[table.name]} rows, found {copied}")
    return counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Copy content into an empty, migrated database.")
    parser.add_argument("source_url", help="e.g. sqlite:///./career_platform.db")
    parser.add_argument("--target-env", default="TARGET_DATABASE_URL", help="env var holding the target URL")
    args = parser.parse_args(argv)

    target_url = os.environ.get(args.target_env)
    if not target_url:
        print(f"Set {args.target_env} to the target database URL.", file=sys.stderr)
        return 2

    target_url = normalize_database_url(target_url)
    source = create_engine(args.source_url)
    target = create_engine(target_url, **engine_options(target_url))
    try:
        counts = copy_content(source, target)
    except TargetNotEmptyError as exc:
        print(exc, file=sys.stderr)
        return 1
    finally:
        source.dispose()
        target.dispose()

    for name, copied in counts.items():
        print(f"{name}: {copied}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the tests on SQLite, then on Postgres**

Run: `.venv/bin/python -m pytest tests/test_content_copy.py -v`
Expected: 5 passed.

Run: `TEST_DATABASE_URL=postgresql://localhost/career_test .venv/bin/python -m pytest tests/test_content_copy.py -v`
Expected: 5 passed. `test_new_rows_after_copy_get_fresh_ids` is the one that proves the sequence reset. Temporarily comment out the `setval` block to confirm it then fails with a duplicate-key `IntegrityError`, then restore the block.

- [ ] **Step 5: Dry-run against the real content (laptop copy; Task 7 copies from the VM)**

```bash
TARGET_DATABASE_URL=postgresql://localhost/career_test .venv/bin/python -c "
from sqlalchemy import create_engine; from app.models import Base
e = create_engine('postgresql+psycopg://localhost/career_test'); Base.metadata.drop_all(e); Base.metadata.create_all(e)"
TARGET_DATABASE_URL=postgresql://localhost/career_test .venv/bin/python -m app.content_copy sqlite:///./career_platform.db
```

Expected output: `certifications: 0`, `education: 1`, `experiences: 3`, `links: 0`, `profiles: 1`, `projects: 3`, `site_meta: 2`, `skills: 7`, `volunteer_work: 2`. The order may differ. A second run exits 1 with `Target already has rows in: …`.

- [ ] **Step 6: Run the whole suite on both databases and commit**

Run: `.venv/bin/python -m pytest -q && TEST_DATABASE_URL=postgresql://localhost/career_test .venv/bin/python -m pytest -q`
Expected: 35 passed, twice.

```bash
git add app/content_copy.py tests/test_content_copy.py
git commit -m "feat: add content copy script for moving SQLite content into Postgres"
```

---

### Task 6: Railway build and deploy config

**Files:**
- Create: `railway.json`
- Create: `.python-version`
- Create: `tests/test_deploy_config.py`

**Interfaces:**
- Consumes: Task 2 (`alembic upgrade head` follows `DATABASE_URL`), `/health` (existing), the `db_engine` fixture (Task 4).
- Produces: Railway builds with Railpack from `uv.lock`, runs migrations only (never a seed) before each deploy, starts uvicorn on `$PORT` trusting the proxy's forwarded headers, and health-checks `/health`.

- [ ] **Step 1: Write the failing guard tests**

These pin "seed stays out of deploy": the deploy commands migrate but never seed, and starting the app and serving every page against an empty database leaves it empty. That second test is what makes Task 7's copy the only way content arrives.

Create `tests/test_deploy_config.py`:

```python
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.main import create_app
from app.models import Base

ROOT = Path(__file__).resolve().parents[1]


def test_deploy_commands_migrate_but_never_seed():
    deploy = json.loads((ROOT / "railway.json").read_text())["deploy"]
    commands = " ".join(deploy["preDeployCommand"] + [deploy["startCommand"]])
    assert "alembic upgrade head" in commands
    assert "seed" not in commands


def test_starting_and_serving_leaves_an_empty_database_empty(db_engine):
    client = TestClient(create_app())
    for path in ["/", "/resume", "/projects", "/contact", "/health"]:
        assert client.get(path).status_code == 200

    with Session(db_engine) as db:
        for table in Base.metadata.sorted_tables:
            assert db.scalar(select(func.count()).select_from(table)) == 0, table.name


def test_start_command_trusts_the_proxys_forwarded_proto():
    start = json.loads((ROOT / "railway.json").read_text())["deploy"]["startCommand"]
    assert '--forwarded-allow-ips="*"' in start


def _non_loopback_ip():
    # Railway's proxy reaches the app from a non-loopback address. Uvicorn trusts
    # 127.0.0.1 by default, so the test must connect from a real interface to be meaningful.
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        try:
            probe.connect(("192.0.2.1", 80))  # TEST-NET-1: no packet is sent for UDP connect
            ip = probe.getsockname()[0]
        except OSError:
            return None
    return None if ip.startswith("127.") else ip


def test_app_behind_proxy_builds_https_urls(tmp_path):
    ip = _non_loopback_ip()
    if ip is None:
        pytest.skip("no non-loopback interface to simulate Railway's proxy")

    with socket.socket() as free:
        free.bind(("", 0))
        port = free.getsockname()[1]
    start = json.loads((ROOT / "railway.json").read_text())["deploy"]["startCommand"]
    env = {
        **os.environ,
        "PORT": str(port),
        "DATABASE_URL": f"sqlite:///{tmp_path / 'empty.db'}",
        "PATH": f"{Path(sys.executable).parent}{os.pathsep}{os.environ['PATH']}",
    }
    server = subprocess.Popen(start, shell=True, cwd=ROOT, env=env,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    try:
        base = f"http://{ip}:{port}"
        for _ in range(50):
            try:
                httpx.get(f"{base}/health", timeout=0.5)
                break
            except httpx.TransportError:
                time.sleep(0.1)
        headers = {"X-Forwarded-Proto": "https"}

        redirect = httpx.get(f"{base}/projects/", headers=headers, follow_redirects=False)
        assert redirect.status_code == 307
        assert redirect.headers["location"].startswith("https://")

        page = httpx.get(f"{base}/", headers=headers).text
        assert 'rel="stylesheet" href="http://' not in page
    finally:
        os.killpg(server.pid, 15)
        server.wait(timeout=10)
```

- [ ] **Step 2: Run them to verify the first fails**

Run: `.venv/bin/python -m pytest tests/test_deploy_config.py -v`
Expected:
- `test_deploy_commands_migrate_but_never_seed`, `test_start_command_trusts_the_proxys_forwarded_proto` and `test_app_behind_proxy_builds_https_urls` FAIL with `FileNotFoundError` for `railway.json`.
- `test_starting_and_serving_leaves_an_empty_database_empty` PASSES already: it guards the current no-seed behavior against regressions.

To see the proxy test fail for the right reason, temporarily create `railway.json` without `--forwarded-allow-ips` and rerun. The redirect assertion fails with an `http://` location. Verified on 2026-10-08: from a non-loopback address, default Uvicorn redirected `/projects/` to `http://…/projects`, and with `--forwarded-allow-ips="*"` to `https://…/projects`.

- [ ] **Step 3: Pin Python**

Create `.python-version` containing exactly:

```
3.12
```

- [ ] **Step 4: Write the Railway config**

Create `railway.json`:

```json
{
  "$schema": "https://railway.com/railway.schema.json",
  "build": {
    "builder": "RAILPACK"
  },
  "deploy": {
    "preDeployCommand": ["alembic upgrade head"],
    "startCommand": "sh -c 'uvicorn app.main:create_app --factory --host 0.0.0.0 --port ${PORT:-8000} --workers 2 --forwarded-allow-ips=\"*\"'",
    "healthcheckPath": "/health",
    "healthcheckTimeout": 60,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 5
  }
}
```

Why each piece:
- `preDeployCommand` runs in a fresh container with the service's variables after the build and before traffic switches. It only migrates the schema. It never seeds, because the content comes from the VM (Task 7). A failed migration stops the deploy and leaves the old one serving.
- `sh -c` expands `$PORT`, which Railway assigns.
- `--workers 2` matches the VM.
- `--forwarded-allow-ips="*"`: Railway's edge terminates HTTPS and forwards plain HTTP with `X-Forwarded-Proto: https`. By default Uvicorn trusts those headers only from `127.0.0.1`, and Railway's proxy isn't loopback, so without this the app thinks every request is `http` and builds `http://` redirects and absolute links. Trusting `*` is safe here because the container has no public port: only Railway's proxy and the project's private network can reach it. The quotes stop `sh` treating `*` as a filename pattern.
- `/health` answers 200 even when the database is degraded. That's intentional, because fallback is the product requirement, so a Postgres outage won't make Railway restart-loop the app.

- [ ] **Step 5: Run the guard tests to verify they pass, then the whole suite**

Run: `.venv/bin/python -m pytest tests/test_deploy_config.py -v`
Expected: 4 passed. The proxy test is skipped only on a machine with no network interface.

Run: `.venv/bin/python -m pytest -q && TEST_DATABASE_URL=postgresql://localhost/career_test .venv/bin/python -m pytest -q`
Expected: 39 passed, twice.

- [ ] **Step 6: Run the start command locally**

```bash
PORT=8123 sh -c 'uvicorn app.main:create_app --factory --host 0.0.0.0 --port ${PORT:-8000} --workers 2 --forwarded-allow-ips="*"' &
sleep 3
curl -s http://127.0.0.1:8123/health
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8123/
kill %1
```

Run it with `.venv/bin` on `PATH`, or prefix `uvicorn` with `.venv/bin/`.
Expected: `{"status":"ok","database":"healthy","fallback":false}`, then `200`.

- [ ] **Step 7: Commit, push the branch, open the PR**

```bash
git add railway.json .python-version tests/test_deploy_config.py docs/superpowers/plans/2026-10-08-railway-postgres-migration.md
git commit -m "chore: add Railway build and deploy config (migrate only, no seed, trust proxy headers)"
git push -u origin feat/railway-postgres
gh pr create --base main --title "Prepare for Railway and PostgreSQL" --body "Postgres driver and URL handling, Alembic follows DATABASE_URL, /admin off in production, Postgres test mode, content copy script, railway.json. Deploys migrate the schema only; content moves once from the VM (plan Task 7). No deploy happens until the Railway web service is connected."
```

- [ ] **Step 8: Merge**

Merge the PR once it's reviewed. The VM is unaffected: it only changes when someone runs `git pull` on it. And if it did pull, SQLite still works, with `/admin` still blocked by nginx.

---

### Task 7: Configure Railway, first deploy, copy the content

Operational task. No code changes. Run commands from the project folder (linked to `renewed-strength`). **No command in this task prints a database URL.**

The first deploy creates empty tables, and nothing seeds them. The VM's rows arrive in Step 6, and that's the only time content is inserted.

- [ ] **Step 1: Set the web service's variables (no deploy yet: there's no source)**

```bash
railway variable set 'DATABASE_URL=${{Postgres.DATABASE_URL}}' --service web --skip-deploys
railway variable set ENVIRONMENT=production --service web --skip-deploys
railway variables --service web --json | python3 -c "import json,sys; print(sorted(json.load(sys.stdin)))"
```

`--json` output includes raw values (the resolved database URL among them), so always pipe it through the key-only filter above. Never print it plainly.

Expected: the key list includes `DATABASE_URL` and `ENVIRONMENT`. Use single quotes so your shell doesn't touch `${{…}}`. Railway resolves it to the private Postgres URL inside the project.

- [ ] **Step 2: Connect the repo (this starts the first deploy)**

Railway dashboard → `renewed-strength` → `web` → Settings → Source → Connect Repo → `gclarke5/career-platform-2-`, branch `main`.

Watch it:

```bash
railway logs --service web --latest --build       # build output
railway logs --service web --latest --deployment  # pre-deploy migration and app start
railway service list
```

`--latest` matters: without it, `railway logs` shows the last *successful* deployment, which on a first deploy doesn't exist yet.

Expected: the build installs from `uv.lock` (psycopg among the packages), the pre-deploy log shows `Running upgrade  -> b2c04cf6e9d4`, `-> c7e1a9d3f2b8`, `-> d4a8f1c2e7b9`, and `web` turns `SUCCESS`.

If the pre-deploy fails, the deploy stops and nothing is served. Read the log:
- `connection refused` or a `localhost` host: `DATABASE_URL` isn't the `${{Postgres.DATABASE_URL}}` reference.
- `alembic: not found`: Railpack didn't put the virtualenv on `PATH`. Change `preDeployCommand` to `["python -m alembic upgrade head"]` and the start command's `uvicorn` to `python -m uvicorn`, then push.

- [ ] **Step 3: Give the service a Railway URL and check the empty-database state**

```bash
railway domain --service web
```

Expected: a `https://web-production-xxxx.up.railway.app` URL. With empty tables:
- `/health` shows `"database":"healthy"`.
- `/` shows the fallback profile (real name and headline) and no "Selected work". That's expected before the copy.
- `/admin` returns 404.

- [ ] **Step 4: Enable Postgres's public TCP proxy (temporary)**

Railway dashboard → `Postgres` → Settings → Networking → TCP Proxy → Enable.

Check the variable exists, without printing it:

```bash
railway variables --service Postgres --json | python3 -c "import json,sys; print('DATABASE_PUBLIC_URL' in json.load(sys.stdin))"
```

Expected: `True`.

- [ ] **Step 5: Snapshot the VM's database and bring it to the laptop**

The rows come from the VM, the live site's database, not the laptop copy. `.backup` takes a consistent snapshot even while the app has the file open; a plain `cp` could catch a half-written page. Use `${VM_IP}` with braces: in zsh, `$VM_IP:c…` is read as a variable modifier.

```bash
VM_IP=$(az vm show -d -g rg-career-platform -n vm-career-platform --query publicIps -o tsv)
ssh -i ~/.ssh/isba4775_azure "azureuser@${VM_IP}" '
  sqlite3 -readonly ~/career-platform-data/career_platform.db ".backup /tmp/vm-content.db" &&
  sqlite3 -readonly /tmp/vm-content.db "pragma integrity_check; select version_num from alembic_version;"'
mkdir -p ../railway-move
scp -i ~/.ssh/isba4775_azure "azureuser@${VM_IP}:/tmp/vm-content.db" ../railway-move/vm-content.db
ssh -i ~/.ssh/isba4775_azure "azureuser@${VM_IP}" 'rm /tmp/vm-content.db'
sqlite3 -readonly ../railway-move/vm-content.db "pragma integrity_check; select version_num from alembic_version; select count(*) from profiles; select count(*) from projects;"
```

Expected: `ok` and `d4a8f1c2e7b9` on the VM. The local check prints `ok`, `d4a8f1c2e7b9`, `1`, `3`.

If the version isn't `d4a8f1c2e7b9`, stop. The VM's schema doesn't match the code Railway just migrated to, and the copy would fail or drop columns.

`../railway-move/` sits outside the repo, so the snapshot can't be committed.

- [ ] **Step 6: Copy the VM's rows into Postgres**

```bash
railway run --service Postgres -- sh -c 'TARGET_DATABASE_URL="$DATABASE_PUBLIC_URL" .venv/bin/python -m app.content_copy sqlite:///../railway-move/vm-content.db'
```

Expected: the copy prints the same nine counts as Task 5 Step 5 (profiles 1, experiences 3, projects 3, skills 7, education 1, site_meta 2, volunteer_work 2, certifications 0, links 0) and exits 0. Exit 1 means Postgres already has content: stop and find out why before going further.

- [ ] **Step 7: Verify on the Railway URL**

```bash
B=https://web-production-xxxx.up.railway.app   # from Step 3
curl -s $B/health
for p in / /resume /projects /projects/mlb-predictive-model /projects/operations-forecasting-intel /contact /projects/nope /admin /static/favicon.svg; do printf "%-40s %s\n" $p "$(curl -s -o /dev/null -w '%{http_code}' $B$p)"; done
curl -s $B/ | grep -o -E 'Analyst in the making[^<]*|What I.ve done so far'
curl -s -o /dev/null -w "redirect: %{redirect_url}\n" $B/projects/
diff <(curl -s https://gavinclarke.me/resume | sed -n '/<main/,/<\/main>/p') <(curl -s $B/resume | sed -n '/<main/,/<\/main>/p') && echo "resume identical to the VM"
```

Expected: `/health` → `"fallback":false`. The `/projects/` redirect starts with `https://`; an `http://` here means the proxy header isn't trusted. Pages 200, `/projects/nope` and `/admin` 404. The headline and "What I've done so far" are present, and the resume's `<main>` is identical to the live VM's.

- [ ] **Step 8: Turn the TCP proxy back off**

Railway dashboard → `Postgres` → Settings → Networking → TCP Proxy → remove it.

Then rerun the Step 4 check. Expected: `False`. The app is unaffected because it uses the private network.

---

### Task 8: Move gavinclarke.me to Railway

DNS is at your registrar, so you'll make those changes yourself. The VM stays up throughout, so rollback is one DNS change.

- [ ] **Step 1: Lower the TTL a day ahead**

At your registrar, set the TTL on the `gavinclarke.me` and `www` records to 300 seconds. Then wait out the old TTL (`dig gavinclarke.me +noall +answer` shows it) before Step 3, so the switch and any rollback take effect within minutes.

- [ ] **Step 2: Add the custom domains in Railway**

```bash
railway domain gavinclarke.me --service web
railway domain www.gavinclarke.me --service web
```

Expected: Railway prints the DNS records to create: a CNAME target, plus a TXT verification record if it asks for one. Note them.

**Decision for you:** the apex `gavinclarke.me` can only point at a CNAME target if your registrar supports CNAME flattening or ALIAS/ANAME records (Cloudflare, Namecheap's ALIAS, Porkbun, etc.). If yours doesn't, either move DNS to one that does, or make `www.gavinclarke.me` the main address and redirect the apex at the registrar.

- [ ] **Step 3: Switch DNS**

At the registrar:
- Replace the apex A record (`20.114.0.108`) with the record Railway gave.
- Add or replace the `www` CNAME.
- Add any TXT verification record.

Leave the VM running.

- [ ] **Step 4: Verify the cutover**

```bash
dig +short gavinclarke.me www.gavinclarke.me
curl -sI https://gavinclarke.me | grep -i -E '^(HTTP|server)'
echo | openssl s_client -connect gavinclarke.me:443 -servername gavinclarke.me 2>/dev/null | openssl x509 -noout -subject -issuer -dates
curl -s https://gavinclarke.me/health
curl -s -o /dev/null -w "%{http_code} %{redirect_url}\n" http://gavinclarke.me/
curl -s -o /dev/null -w "%{http_code}\n" https://gavinclarke.me/admin
curl -s -o /dev/null -w "%{redirect_url}\n" https://gavinclarke.me/projects/
```

Expected:
- `dig` no longer shows `20.114.0.108`.
- The server header is Railway's edge, not `nginx/1.24.0 (Ubuntu)`.
- The certificate subject is `gavinclarke.me` with a valid date range.
- `/health` returns `"fallback":false`.
- `http://` redirects to `https://`.
- `/admin` returns 404.
- The `/projects/` redirect points to `https://gavinclarke.me/projects`.
- In a browser, the page is styled and the console shows no mixed-content warnings.

Railway issues the certificate after DNS verifies, which can take a few minutes up to about an hour.

**Rollback:** put the A record back to `20.114.0.108` and remove the CNAME. The VM is still serving the same content.

- [ ] **Step 5: After 7 stable days, retire the VM as the host**

This is a separate decision, and it's yours. Stopping `career-platform` and `nginx` on the VM, or deallocating it to stop Azure charges, is irreversible in practice: Certbot's certificate and the nginx config would need redoing to go back.

Before you do it, keep a copy of the VM's database: `scp` `~/career-platform-data/career_platform.db.pre-2026-10-08` and the current file to your laptop.

- [ ] **Step 6: Update the docs that describe the old host**

`docs/how-this-site-is-secured.md` (on branch `docs/how-this-site-is-secured`) describes nginx and Certbot on the VM. After cutover, TLS terminates at Railway's edge. Update that doc, or note that it describes the pre-Railway setup, before you merge it.

---

## After the move: how content changes

The laptop SQLite file stops being the source of truth. Postgres on Railway is.

- **To change content:** enable the TCP proxy, then run `railway connect Postgres` for a `psql` shell, make the change, and disable the proxy again.
- **Keep the fallback in step:** after any change to the profile, experience, projects, or `site_meta`, update `app/fallback_data.py` to match.
- **Schema changes:** add a migration as before. Merging to `main` deploys it, and the pre-deploy step runs it before the new code serves traffic.
- **Backups:** Railway's Postgres backups are configured on the Postgres service (Settings → Backups). Turn them on before cutover. The laptop SQLite stays as an offline snapshot of the content as of the copy.
