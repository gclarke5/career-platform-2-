from fastapi.testclient import TestClient

from app.main import create_app


def test_health_reports_database_state():
    data = TestClient(create_app()).get("/health").json()
    assert data["database"] == "healthy"
    assert data["fallback"] is False
