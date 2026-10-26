from fastapi.testclient import TestClient

from app.main import create_app


def test_health_reports_database_state():
    data = TestClient(create_app()).get("/health").json()
    assert data["database"] == "healthy"
    assert data["fallback"] is False


def test_health_reports_deployed_commit(monkeypatch):
    monkeypatch.setenv("RAILWAY_GIT_COMMIT_SHA", "0123456789abcdef0123456789abcdef01234567")
    assert TestClient(create_app()).get("/health").json()["commit"] == "0123456"


def test_health_commit_is_null_outside_railway(monkeypatch):
    monkeypatch.delenv("RAILWAY_GIT_COMMIT_SHA", raising=False)
    assert TestClient(create_app()).get("/health").json()["commit"] is None
