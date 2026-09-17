from fastapi.testclient import TestClient

from app.main import create_app


def test_admin_route_exists():
    response = TestClient(create_app()).get("/admin")
    assert response.status_code == 200
    assert response.json()["profile"]["full_name"] == "Alex Morgan"


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
