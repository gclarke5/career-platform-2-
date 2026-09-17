from fastapi.testclient import TestClient

from app.main import create_app


def test_create_app_returns_fastapi_app():
    app = create_app()
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
