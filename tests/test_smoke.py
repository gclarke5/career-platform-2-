from fastapi.testclient import TestClient

from app.main import create_app


def test_smoke_routes_load():
    client = TestClient(create_app())
    for path in ["/", "/health", "/resume", "/projects", "/contact"]:
        assert client.get(path).status_code == 200
