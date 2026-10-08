import asyncio
import time

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import normalize_database_url
from app.db import engine_options
from app.main import create_app


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        ("postgresql://u:p@host:5432/db", "postgresql+psycopg://u:p@host:5432/db"),
        ("postgres://u:p@host:5432/db", "postgresql+psycopg://u:p@host:5432/db"),
        ("postgresql+psycopg://u:p@host/db", "postgresql+psycopg://u:p@host/db"),
        ("sqlite:///./career_platform.db", "sqlite:///./career_platform.db"),
    ],
)
def test_normalize_database_url(given, expected):
    assert normalize_database_url(given) == expected


def test_engine_options_for_sqlite_allow_cross_thread_use():
    assert engine_options("sqlite:///./x.db") == {"connect_args": {"check_same_thread": False}}


def test_engine_options_for_postgres_fail_fast_and_ping():
    options = engine_options("postgresql+psycopg://u:p@host/db")
    assert options["connect_args"] == {"connect_timeout": 2}
    assert options["pool_pre_ping"] is True


def test_pages_fall_back_quickly_when_postgres_is_unreachable(monkeypatch):
    # 10.255.255.1 is non-routable: connections hang rather than being refused,
    # which is what a dead database looks like from the app.
    url = "postgresql+psycopg://user:pass@10.255.255.1:5432/db"
    engine = create_engine(url, **engine_options(url))
    monkeypatch.setattr("app.db.SessionLocal", sessionmaker(bind=engine))
    monkeypatch.setattr("app.main.engine", engine)

    started = time.monotonic()
    response = TestClient(create_app()).get("/")
    elapsed = time.monotonic() - started

    assert response.status_code == 200
    assert "Gavin Clarke" in response.text
    assert elapsed < 10


@pytest.mark.parametrize("path", ["/", "/resume", "/projects", "/projects/mlb-predictive-model", "/contact"])
def test_one_failed_connection_per_request_sends_every_page_to_fallback(monkeypatch, path):
    # /resume makes six reads; each must not wait out its own connect timeout.
    url = "postgresql+psycopg://user:pass@10.255.255.1:5432/db"
    engine = create_engine(url, **engine_options(url))
    monkeypatch.setattr("app.db.SessionLocal", sessionmaker(bind=engine))

    started = time.monotonic()
    response = TestClient(create_app()).get(path)
    elapsed = time.monotonic() - started

    assert response.status_code == 200
    assert "Gavin Clarke" in response.text
    assert elapsed < 5, f"{path} took {elapsed:.1f}s"


def test_concurrent_visitors_during_outage_are_served_in_parallel(monkeypatch):
    # Blocking DB calls inside async routes would freeze the event loop, so three
    # visitors would wait ~2s each in turn. Served in parallel, they share one ~2s wait.
    url = "postgresql+psycopg://user:pass@10.255.255.1:5432/db"
    engine = create_engine(url, **engine_options(url))
    monkeypatch.setattr("app.db.SessionLocal", sessionmaker(bind=engine))
    app = create_app()

    async def three_visitors():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await asyncio.gather(*(client.get("/contact") for _ in range(3)))

    started = time.monotonic()
    responses = asyncio.run(three_visitors())
    elapsed = time.monotonic() - started

    assert all(r.status_code == 200 and "Gavin Clarke" in r.text for r in responses)
    assert elapsed < 4, f"three concurrent requests took {elapsed:.1f}s"
