import pytest
from fastapi.testclient import TestClient

from app.main import create_app


def test_admin_route_exists():
    response = TestClient(create_app()).get("/admin")
    assert response.status_code == 200
    assert response.json()["profile"]["full_name"] == "Gavin Clarke"


def test_admin_profile_update_changes_structured_payload():
    response = TestClient(create_app()).put(
        "/admin/profile",
        json={
            "full_name": "Jordan Lee",
            "headline": "Analytics Builder",
            "summary": "Turns data into decisions.",
            "email": "jordan@example.com",
        },
    )
    assert response.status_code == 200
    assert response.json()["profile"]["full_name"] == "Jordan Lee"


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


@pytest.mark.parametrize("environment", ["Production", "prod", "staging", ""])
def test_admin_stays_hidden_unless_environment_is_explicitly_development(monkeypatch, environment):
    monkeypatch.setattr("app.main.settings.environment", environment)
    assert TestClient(create_app()).get("/admin").status_code == 404


def test_admin_stays_hidden_on_railway_even_if_environment_is_unset(monkeypatch):
    # Railway sets RAILWAY_ENVIRONMENT on every service; a forgotten ENVIRONMENT
    # variable falls back to "development" and must not reopen /admin there.
    monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
    assert TestClient(create_app()).get("/admin").status_code == 404
