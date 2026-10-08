import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import create_app
from app.models import Education, Experience, Profile, Project, Skill, VolunteerWork


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
                ),
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
    assert "Alex Morgan" not in page


def test_missing_github_url_hides_github_link(seeded, client):
    for path in ["/", "/contact"]:
        page = client.get(path).text
        assert "GitHub" not in page
        assert 'href="None"' not in page


def test_resume_shows_experience_education_skills_and_volunteer_work(seeded, client):
    page = client.get("/resume").text
    assert "Data Analyst Intern" in page
    assert "Acme Analytics · January 2025 - Present" in page
    assert "<li>Researched outlier teams</li>" in page
    assert "Example University" in page
    assert "Courses: Statistics" in page
    assert "Technical" in page and "SQL" in page
    assert "Professional" in page and "Communications" in page
    assert "Volunteer Work" in page
    assert "Food Drive Volunteer" in page
    assert "Northstar Fintech" not in page


def test_projects_come_from_database(seeded, client):
    listing = client.get("/projects").text
    assert "Demand Forecast" in listing
    assert "Revenue Forecasting Platform" not in listing

    detail = client.get("/projects/demand-forecast")
    assert detail.status_code == 200
    assert "<li>Compared moving average projections</li>" in detail.text
    assert "Impact:" not in detail.text
    assert client.get("/projects/revenue-forecasting-platform").status_code == 404


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
    for path in ["/", "/resume", "/projects", "/projects/revenue-forecasting-platform", "/contact"]:
        assert client.get(path).status_code == 200
    assert "Alex Morgan" in client.get("/").text
    assert "Northstar Fintech" in client.get("/resume").text
