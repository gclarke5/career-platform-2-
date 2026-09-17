from fastapi.testclient import TestClient

from app.main import create_app


def test_public_pages_render_profile_and_core_routes():
    client = TestClient(create_app())
    for path in ["/", "/resume", "/projects", "/contact"]:
        response = client.get(path)
        assert response.status_code == 200
    assert "Alex Morgan" in client.get("/").text


def test_project_detail_returns_not_found_for_unknown_slug():
    assert TestClient(create_app()).get("/projects/missing").status_code == 404
