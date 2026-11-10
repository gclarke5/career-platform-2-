"""Off Railway nothing sets RAILWAY_ENVIRONMENT, so the settings themselves must fail closed."""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings
from app.main import create_app

POSTGRES_URL = "postgresql://u:p@db.example.com:5432/career_platform"


def test_environment_defaults_to_production(monkeypatch):
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    assert Settings(_env_file=None, database_url=POSTGRES_URL).environment == "production"


def test_admin_is_hidden_with_default_settings_off_railway(monkeypatch):
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)
    defaults = Settings(_env_file=None, database_url=POSTGRES_URL)
    monkeypatch.setattr("app.main.settings", defaults)
    assert TestClient(create_app()).get("/admin").status_code == 404


@pytest.mark.parametrize("environment", ["production", "staging", ""])
def test_sqlite_is_refused_outside_development(environment):
    with pytest.raises(ValidationError, match="DATABASE_URL"):
        Settings(_env_file=None, environment=environment, database_url="sqlite:///./career_platform.db")


def test_sqlite_is_refused_when_database_url_is_missing_in_production(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    with pytest.raises(ValidationError, match="DATABASE_URL"):
        Settings(_env_file=None)


def test_sqlite_is_allowed_in_development():
    s = Settings(_env_file=None, environment="development", database_url="sqlite:///./career_platform.db")
    assert s.database_url.startswith("sqlite")


def test_postgres_is_allowed_in_production():
    s = Settings(_env_file=None, environment="production", database_url=POSTGRES_URL)
    assert s.database_url.startswith("postgresql+psycopg://")
