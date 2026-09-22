# Resume Career Platform Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a FastAPI-based resume and portfolio site whose public profile remains visible even when SQLite is unavailable, using a documented fallback strategy and a clean data model.

**Architecture:** The app will use a small Python web service with FastAPI, SQLAlchemy, and SQLite for structured content, plus a static fallback payload that serves the core profile and contact information during outages. Pages will render from shared templates and CSS, with a data layer that supports both live database reads and graceful degraded-mode reads.

**Tech Stack:** Python 3.12+, uv, FastAPI, Uvicorn, Jinja2, SQLite, SQLAlchemy 2.x, Alembic, pytest, HTTPX/TestClient, plain CSS, local Codespaces deployment, Azure VM deployment target.

**Spec:** `docs/superpowers/specs/resume-career-platform-spec.md`

## Global Constraints

- The site must remain available even if database connectivity is temporarily unavailable.
- The core profile must remain visible even if database connectivity is temporarily unavailable.
- The candidate profile must not disappear behind a blank, maintenance, or database-error screen while the site is still reachable.
- The fallback should retain the most important public-facing information, not just a generic maintenance page.
- The site must support structured content for profile information, experience, projects, skills, education, certifications, links, contact info, and site metadata.
- Public-facing design must feel professional, modern, credible, and easy to scan.
- The implementation target is a local Codespaces setup with an Azure VM deployment target.

---

### Task 1: Scaffold the app, environment, and configuration

**Files:**
- Create: `app/__init__.py`, `app/config.py`, `app/main.py`, `requirements.txt`, `README.md` (if needed)
- Create: `tests/test_config.py`, `tests/test_app_startup.py`

**Interfaces:**
- Consumes: no prior app code
- Produces:
  - `Settings` from `app.config`
  - `create_app()` from `app.main`
  - application startup and health endpoints for later tasks

- [ ] **Step 1: Write the failing test for app startup and config defaults**

```python
# tests/test_app_startup.py
from fastapi.testclient import TestClient
from app.main import create_app


def test_create_app_returns_fastapi_app():
    app = create_app()
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_app_startup.py -q`
Expected: FAIL with `ModuleNotFoundError` or `ImportError` because the app is not scaffolded yet.

- [ ] **Step 3: Write the minimal implementation**

```python
# app/config.py
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Career Platform"
    database_url: str = "sqlite:///./career_platform.db"
    environment: str = "development"

    class Config:
        env_file = ".env"


settings = Settings()
```

```python
# app/main.py
from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="Career Platform")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `pytest tests/test_app_startup.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/main.py app/config.py tests/test_app_startup.py
git commit -m "feat: scaffold career platform app"
```

**Done looks like:**
- FastAPI app boots cleanly.
- `/health` returns `{"status":"ok"}`.
- App configuration reads environment settings and has a default SQLite URL.

**How to check it:**
- Run `uvicorn app.main:create_app --factory` and hit `/health`.
- Confirm the app starts with no import errors.

---

### Task 2: Define the data model and database schema

**Files:**
- Create: `app/db.py`, `app/models.py`, `app/schemas.py`
- Create: `migrations/` (Alembic folder) and `alembic.ini`
- Create: `tests/test_models.py`

**Interfaces:**
- Consumes: app config and app startup
- Produces:
  - `Profile`, `Experience`, `Project`, `Skill`, `Education`, `Certification`, `Link`, `SiteMeta`
  - `get_db()` session factory
  - ORM models for later page rendering and fallback data checks

- [ ] **Step 1: Write the failing model test**

```python
# tests/test_models.py
from app.models import Profile


def test_profile_model_has_required_fields():
    profile = Profile(
        full_name="Alex Morgan",
        headline="Analytics & Product Leader",
        summary="Builds data products with measurable business impact.",
        email="alex@example.com",
    )
    assert profile.full_name == "Alex Morgan"
    assert profile.headline == "Analytics & Product Leader"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_models.py -q`
Expected: FAIL because the model file is not created yet.

- [ ] **Step 3: Write the minimal ORM implementation**

```python
# app/models.py
from sqlalchemy import String, Text, Integer, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    headline: Mapped[str] = mapped_column(String(180), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    github_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location: Mapped[str | None] = mapped_column(String(120), nullable=True)
```

Add analogous `Experience`, `Project`, `Skill`, and `SiteMeta` models with their required relationships and arrays of references.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_models.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/models.py app/db.py app/schemas.py tests/test_models.py
git commit -m "feat: add profile and portfolio schema"
```

**Done looks like:**
- A migration-ready SQLAlchemy schema exists for profile, experience, projects, skills, and metadata.
- Models reflect the spec’s required content groups and support future admin editing.

**How to check it:**
- Run `alembic revision --autogenerate -m "init schema"` and verify migrations are captured.
- Open SQLite to confirm tables exist and their columns match the required fields.

---

### Task 3: Add database-backed read/write flow and a graceful fallback layer

**Files:**
- Create: `app/repositories.py`, `app/fallback_data.py`, `app/services/profile_service.py`
- Modify: `app/main.py`, `app/db.py`
- Create: `tests/test_fallback_profile.py`, `tests/test_profile_service.py`

**Interfaces:**
- Consumes: ORM models and SQLAlchemy session factory
- Produces:
  - `get_profile_payload()` returns the best available profile data
  - `get_fallback_profile()` returns the static emergency profile payload
  - `DatabaseUnavailableError` / `read_profile_data()` strategy for degraded mode

- [ ] **Step 1: Write the failing fallback test**

```python
# tests/test_fallback_profile.py
from app.fallback_data import fallback_profile


def test_fallback_profile_keeps_core_identity_visible():
    assert fallback_profile["full_name"]
    assert fallback_profile["headline"]
    assert fallback_profile["summary"]
    assert "contact" in fallback_profile
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_fallback_profile.py -q`
Expected: FAIL because fallback data does not exist yet.

- [ ] **Step 3: Implement the fallback payload and service logic**

```python
# app/fallback_data.py
fallback_profile = {
    "full_name": "Alex Morgan",
    "headline": "Analytics & Product Leader",
    "summary": "Builds data products with measurable business impact.",
    "email": "alex@example.com",
    "linkedin_url": "https://www.linkedin.com/in/alexmorgan",
    "github_url": "https://github.com/alexmorgan",
    "cta_primary": "View Resume",
    "contact": {
        "email": "alex@example.com",
        "linkedin": "https://www.linkedin.com/in/alexmorgan",
    },
}
```

```python
# app/services/profile_service.py
from app.fallback_data import fallback_profile


def get_profile_payload(db_session=None):
    if db_session is None:
        return fallback_profile
    try:
        # query live DB here
        return fallback_profile
    except Exception:
        return fallback_profile
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_fallback_profile.py tests/test_profile_service.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/fallback_data.py app/services/profile_service.py tests/test_fallback_profile.py
git commit -m "feat: add fallback profile and degraded mode data"
```

**Done looks like:**
- The app reads live database content when available and falls back to a structured profile payload when DB access fails.
- Name, headline, summary, contact links, and CTA remain present during degraded mode.
- There is no generic error-only page while the site is reachable.

**How to check it:**
- Simulate a DB failure and hit the home route. The page should still render profile identity and contact links.
- Confirm the fallback payload includes the candidate’s identity and primary CTA.

---

### Task 4: Build the public pages and templates

**Files:**
- Create: `app/routes/__init__.py`, `app/routes/public.py`
- Create: `templates/base.html`, `templates/index.html`, `templates/resume.html`, `templates/project_detail.html`, `templates/contact.html`
- Create: `static/css/styles.css`
- Create: `tests/test_public_routes.py`

**Interfaces:**
- Consumes: profile, project, and experience payloads from services
- Produces: rendered pages for home, resume, project detail, and contact routes

- [ ] **Step 1: Write the failing route tests**

```python
# tests/test_public_routes.py
from fastapi.testclient import TestClient
from app.main import create_app


def test_home_page_renders_profile_identity_even_when_db_unavailable():
    app = create_app()
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "Alex Morgan" in response.text
```

- [ ] **Step 2: Run the route tests to verify they fail**

Run: `pytest tests/test_public_routes.py -q`
Expected: FAIL because routes/templates are not implemented yet.

- [ ] **Step 3: Implement routes and templates**

`app/routes/public.py` should include:
- `GET /` home page
- `GET /resume` structured resume view
- `GET /projects` list of project cards
- `GET /projects/{slug}` project detail page
- `GET /contact` contact page

HTML will use Jinja2 and shared CSS classes. The home page must always expose name, headline, summary, contact links, and CTA; the resume view can use the fallback or live content depending on DB health.

- [ ] **Step 4: Run the route tests to verify they pass**

Run: `pytest tests/test_public_routes.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/routes app/templates static/css/styles.css tests/test_public_routes.py
git commit -m "feat: add public portfolio pages"
```

**Done looks like:**
- The public site has home, resume, project detail, and contact pages.
- The front page clearly shows the candidate identity and CTA even in degraded mode.
- Styling matches a polished, modern personal brand.

**How to check it:**
- Run the app locally and visit `/`, `/resume`, `/contact`.
- Verify the page shows the same identity and contact data when the database is forced offline.

---

### Task 5: Add database health checks and automatic fallback monitoring

**Files:**
- Modify: `app/main.py`, `app/config.py`, `app/services/profile_service.py`
- Create: `tests/test_health_checks.py`

**Interfaces:**
- Consumes: SQLAlchemy engine and DB session factory
- Produces:
  - a health endpoint that reports database state
  - fallback-aware logic for content reads

- [ ] **Step 1: Write the failing health-check test**

```python
# tests/test_health_checks.py
from fastapi.testclient import TestClient
from app.main import create_app


def test_health_reports_db_state():
    app = create_app()
    client = TestClient(app)
    response = client.get("/health")
    data = response.json()
    assert "database" in data
```

- [ ] **Step 2: Run the health tests to verify they fail**

Run: `pytest tests/test_health_checks.py -q`
Expected: FAIL because health output is not yet expanded.

- [ ] **Step 3: Implement the health check**

```python
@app.get("/health")
def health() -> dict[str, object]:
    db_ok = check_database()
    return {
        "status": "ok" if db_ok else "degraded",
        "database": "healthy" if db_ok else "unavailable",
        "fallback": not db_ok,
    }
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_health_checks.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/main.py app/services/profile_service.py tests/test_health_checks.py
git commit -m "feat: add degraded-mode health checks"
```

**Done looks like:**
- The app can detect whether the database is healthy or unavailable.
- The app exposes a health signal that allows operators to confirm when the fallback is active.
- Recovery gating is in place before switching fully back to live data.

**How to check it:**
- Run the health endpoint with the DB present and then with the DB intentionally disabled.
- Confirm the response switches between `healthy` and `unavailable` and that the site still renders identity data.

---

### Task 6: Add admin/data entry flow and seed data for initial launch

**Files:**
- Create: `app/routes/admin.py`, `templates/admin.html`
- Create: `app/seed_data.py`
- Modify: `app/main.py`
- Create: `tests/test_admin_routes.py`

**Interfaces:**
- Consumes: profile and content models
- Produces: editing endpoints for structured entries and initial seed content for local runbooks

- [ ] **Step 1: Write the failing admin smoke test**

```python
# tests/test_admin_routes.py
from fastapi.testclient import TestClient
from app.main import create_app


def test_admin_route_exists():
    app = create_app()
    client = TestClient(app)
    response = client.get("/admin")
    assert response.status_code in {200, 401}
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_admin_routes.py -q`
Expected: FAIL because `/admin` is not defined yet.

- [ ] **Step 3: Implement the admin surface**

- Add simple admin route scaffolding for viewing seed data and updating profile/project entries.
- Include a small number of starter records for profile, projects, skills, and contact links.
- Keep admin complexity intentionally simple for v1 and focus on structured data rather than transient login complexity.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_admin_routes.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/routes/admin.py app/seed_data.py templates/admin.html tests/test_admin_routes.py
git commit -m "feat: add admin scaffolding and seed data"
```

**Done looks like:**
- Structured content can be managed in a database-backed flow without manual hardcoded edits for every update.
- A starter portfolio dataset exists for local development and the first live deploy.

**How to check it:**
- Open `/admin` locally.
- Confirm that profile and portfolio entries are visible and editable in a simple form or listing view.

---

### Task 7: Deployment readiness and QA pass

**Files:**
- Create: `Dockerfile` (optional) or deployment config
- Modify: `README.md`
- Create: `tests/test_smoke.py`

**Interfaces:**
- Consumes: app and environment config
- Produces: build and deploy confidence for local Codespaces and Azure VM targets

- [ ] **Step 1: Write the smoke test**

```python
# tests/test_smoke.py
from fastapi.testclient import TestClient
from app.main import create_app


def test_smoke_routes_load():
    app = create_app()
    client = TestClient(app)
    for path in ["/", "/health", "/resume", "/contact"]:
        response = client.get(path)
        assert response.status_code == 200
```

- [ ] **Step 2: Run the smoke test to verify it fails or passes depending on current state**

Run: `pytest tests/test_smoke.py -q`
Expected: initial pass after previous tasks, or fail if one route is still missing.

- [ ] **Step 3: Validate deployment configuration**

- Confirm `uv` install steps, `uvicorn` invocation, environment variables, and Azure VM runbook are documented.
- Ensure the app can run in local Codespaces and be served from Azure VM with SQLite data persisted to a durable local path.
- Add an explicit startup note that the fallback profile must remain visible if the DB is unavailable.

- [ ] **Step 4: Run the full targeted test suite**

Run: `pytest tests -q`
Expected: all application tests pass.

- [ ] **Step 5: Commit**

```bash
git add README.md tests/test_smoke.py .
git commit -m "feat: finalize deployment readiness and QA"
```

**Done looks like:**
- The app is runnable from Codespaces and deployable to Azure VM.
- Manual and automated verification cover homepage, health status, fallback profile visibility, and resume/contact pages.

**How to check it:**
- Start the app locally with `uvicorn` and verify pages render.
- Restart with the DB disabled and confirm the main profile remains visible.
- Review the deployment notes to confirm the app can be launched in the target environment.

---

## Verification Summary

The implementation is accepted when all of the following are true:
- `pytest tests -q` passes.
- `/health` returns status and DB availability information.
- `/` renders name, headline, summary, and contact links when the database is offline.
- `/resume` and `/contact` remain functional in degraded mode.
- Data entry is possible from the admin scaffolding without manual hardcoded edits.
- The app is documented for local Codespaces usage and Azure VM deployment.

This plan is ready for review. If you approve it, I’ll move to implementation using the task sequence above without changing the architecture or scope.