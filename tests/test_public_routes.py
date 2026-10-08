from fastapi.testclient import TestClient

from app.main import create_app


def test_public_pages_render_profile_and_core_routes():
    client = TestClient(create_app())
    for path in ["/", "/resume", "/projects", "/contact"]:
        response = client.get(path)
        assert response.status_code == 200
    assert "Gavin Clarke" in client.get("/").text


def test_project_detail_returns_not_found_for_unknown_slug():
    response = TestClient(create_app()).get("/projects/missing")
    assert response.status_code == 404
    assert "text/html" in response.headers["content-type"]
    assert 'href="/projects"' in response.text


def test_unknown_admin_routes_keep_json_errors():
    response = TestClient(create_app()).get("/admin/missing")
    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}


def test_public_pages_and_health_answer_head_requests():
    client = TestClient(create_app())
    for path in ["/", "/resume", "/projects", "/contact", "/health"]:
        assert client.head(path).status_code == 200
