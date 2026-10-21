import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.main import create_app
from app.models import Education, Experience, Profile, Project, SiteMeta, Skill, VolunteerWork


@pytest.fixture
def seeded(session_factory):
    with session_factory() as db:
        db.add_all(
            [
                Profile(
                    full_name="Jamie Rivera",
                    headline="Business Analytics Student",
                    summary="Builds forecasting models.",
                    email="jamie@example.edu",
                    linkedin_url="https://www.linkedin.com/in/jamie",
                    github_url=None,
                    location="Irvine, CA",
                    cta_primary="View Resume",
                ),
                Experience(
                    title="Data Analyst Intern",
                    company="Acme Analytics",
                    start_date="January 2025",
                    end_date="Present",
                    summary="Built predictive models.",
                    highlights="Researched outlier teams\nReported findings to managers",
                ),
                Project(
                    title="Demand Forecast",
                    slug="demand-forecast",
                    short_summary="Forecasted chip demand.",
                    description="Cleaned data in Excel\nCompared moving average projections",
                    metrics=None,
                    tools="Excel",
                    category="Operations & supply chain",
                ),
                SiteMeta(key="availability", value="Open to analyst roles."),
                SiteMeta(key="proof_points", value="Forecasted chip demand|/projects/demand-forecast|Coursework"),
                Skill(name="SQL", category="Technical"),
                Skill(name="Communications", category="Professional"),
                Education(school="Example University", degree="B.S. Analytics", details="Courses: Statistics"),
                VolunteerWork(
                    role="Food Drive Volunteer",
                    organization="Food drives",
                    start_date="February 2012",
                    end_date="Present",
                    summary="Worked at food drives.",
                ),
            ]
        )
        db.commit()


@pytest.fixture
def client():
    return TestClient(create_app())


def test_home_and_nav_show_database_profile(seeded, client):
    page = client.get("/").text
    assert "Jamie Rivera" in page
    assert "Business Analytics Student" in page
    assert "Gavin Clarke" not in page


def test_missing_github_url_hides_github_link(seeded, client):
    for path in ["/", "/contact"]:
        page = client.get(path).text
        assert "GitHub" not in page
        assert 'href="None"' not in page


def test_resume_shows_experience_education_skills_and_volunteer_work(seeded, client):
    page = client.get("/resume").text
    assert "Data Analyst Intern" in page
    assert "Acme Analytics" in page
    assert "January 2025 - Present" in page
    assert "<li>Researched outlier teams</li>" in page
    assert "Example University" in page
    assert "Relevant coursework" in page
    assert "<li>Statistics</li>" in page
    assert "Technical" in page and "SQL" in page
    assert "Professional" in page and "Communications" in page
    assert "Volunteer Work" in page
    assert "Food Drive Volunteer" in page
    assert "OnPointe, Wells Fargo" not in page


def test_projects_come_from_database(seeded, client):
    response = client.get("/projects")
    assert response.status_code == 200
    listing = response.text
    assert "Demand Forecast" in listing
    assert "Portfolio Performance and Asset Allocation Analysis" not in listing

    detail = client.get("/projects/demand-forecast")
    assert detail.status_code == 200
    assert "<li>Compared moving average projections</li>" in detail.text
    assert "Impact:" not in detail.text
    assert client.get("/projects/portfolio-performance-asset-allocation").status_code == 404


def test_resume_still_renders_when_volunteer_table_is_missing(seeded, client, db_engine):
    with db_engine.begin() as connection:
        connection.execute(text("DROP TABLE volunteer_work"))
    response = client.get("/resume")
    assert response.status_code == 200
    assert "Data Analyst Intern" in response.text
    assert "Volunteer Work" not in response.text


def test_pages_fall_back_when_database_has_no_tables(client, db_engine):
    from app.models import Base

    Base.metadata.drop_all(db_engine)
    for path in ["/resume", "/contact"]:
        assert client.get(path).status_code == 200
    assert "Gavin Clarke" in client.get("/").text
    assert "OnPointe, Wells Fargo" in client.get("/resume").text


@pytest.fixture
def unreachable_database(monkeypatch, tmp_path):
    """Point requests at a database file that can't be opened, like a Postgres outage."""
    engine = create_engine(f"sqlite:///{tmp_path / 'missing-dir' / 'down.db'}")
    monkeypatch.setattr("app.db.SessionLocal", sessionmaker(bind=engine))
    yield
    engine.dispose()


FALLBACK_PROJECT_TITLES = [
    "Portfolio Performance and Asset Allocation Analysis",
    "Operations and Forecasting Project",
]


@pytest.mark.parametrize("path", ["/", "/projects"])
def test_project_pages_return_503_with_profile_when_database_is_down(unreachable_database, client, path):
    response = client.get(path)
    assert response.status_code == 503
    assert "Projects temporarily unavailable" in response.text
    assert "Gavin Clarke" in response.text
    for title in FALLBACK_PROJECT_TITLES:
        assert title not in response.text


def test_project_detail_returns_503_when_database_is_down(unreachable_database, client):
    response = client.get("/projects/mlb-predictive-model")
    assert response.status_code == 503
    assert "Projects temporarily unavailable" in response.text


@pytest.mark.parametrize("path", ["/", "/projects"])
def test_empty_projects_table_says_so(client, path):
    response = client.get(path)
    assert response.status_code == 200
    assert "No projects yet" in response.text
    for title in FALLBACK_PROJECT_TITLES:
        assert title not in response.text


def test_projects_return_after_database_recovers_without_restart(seeded, client, db_engine, session_factory):
    Project.__table__.drop(db_engine)
    assert client.get("/projects").status_code == 503

    Project.__table__.create(db_engine)
    with session_factory() as db:
        db.add(Project(title="Demand Forecast", slug="demand-forecast", short_summary="Forecasted chip demand."))
        db.commit()

    response = client.get("/projects")
    assert response.status_code == 200
    assert "Demand Forecast" in response.text


def test_home_shows_availability_proof_and_selected_work_from_database(seeded, client):
    page = client.get("/").text
    assert "Open to analyst roles." in page
    assert 'href="/projects/demand-forecast"' in page
    assert "Coursework" in page
    assert "Operations &amp; supply chain" in page


def test_project_detail_links_back_to_project_list(seeded, client):
    page = client.get("/projects/demand-forecast").text
    assert 'href="/projects"' in page
