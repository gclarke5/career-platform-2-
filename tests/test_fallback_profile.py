from unittest.mock import Mock

from app.fallback_data import fallback_profile
from app.repositories import DatabaseUnavailableError
from app.services.profile_service import get_profile_payload


def test_fallback_profile_keeps_core_identity_visible():
    assert fallback_profile["full_name"]
    assert fallback_profile["headline"]
    assert fallback_profile["summary"]
    assert fallback_profile["contact"]


def test_profile_service_uses_fallback_when_database_is_unavailable(monkeypatch):
    def fail_read(_db):
        raise DatabaseUnavailableError("database offline")

    monkeypatch.setattr("app.services.profile_service.read_profile_data", fail_read)

    profile = get_profile_payload(Mock())

    assert profile["full_name"] == fallback_profile["full_name"]
    assert profile["headline"] == fallback_profile["headline"]
    assert profile["summary"] == fallback_profile["summary"]
    assert profile["contact"] == fallback_profile["contact"]
