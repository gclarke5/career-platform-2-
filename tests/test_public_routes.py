from fastapi.testclient import TestClient

from app.main import create_app


def test_public_pages_render_profile_and_core_routes():
    client = TestClient(create_app())
    for path in ["/", "/resume", "/projects", "/contact", "/privacy"]:
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
    for path in ["/", "/resume", "/projects", "/contact", "/privacy", "/health"]:
        assert client.head(path).status_code == 200


def test_footer_links_to_privacy_page():
    client = TestClient(create_app())
    assert 'href="/privacy"' in client.get("/").text
    privacy = client.get("/privacy").text
    assert "Google Analytics" in privacy
    assert 'href="/privacy" aria-current="page"' in privacy


def test_analytics_and_banner_are_off_without_a_measurement_id():
    html = TestClient(create_app()).get("/").text
    assert "consent-banner" not in html
    assert "googletagmanager" not in html


def test_analytics_loads_only_through_the_opt_in_script(monkeypatch):
    from app.routes.public import templates

    monkeypatch.setitem(templates.env.globals, "analytics_id", "G-TEST123")
    html = TestClient(create_app()).get("/").text
    assert 'id="consent-banner"' in html
    assert 'data-ga-id="G-TEST123"' in html
    assert 'id="consent-settings"' in html
    # Google's tag is never in the page itself; consent.js injects it after Accept.
    assert "googletagmanager" not in html
