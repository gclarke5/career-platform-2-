import copy

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import fallback_data
from app.models import Base


@pytest.fixture
def db_engine(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False})
    yield engine
    engine.dispose()


@pytest.fixture
def session_factory(db_engine):
    return sessionmaker(bind=db_engine, autoflush=False, autocommit=False)


@pytest.fixture(autouse=True)
def isolated_database(monkeypatch, db_engine, session_factory):
    """Point the app at a throwaway SQLite file so tests never touch ./career_platform.db."""
    Base.metadata.create_all(db_engine)
    monkeypatch.setattr("app.db.SessionLocal", session_factory)
    monkeypatch.setattr("app.main.engine", db_engine)


@pytest.fixture(autouse=True)
def restore_fallback_profile():
    """/admin/profile mutates the shared fallback profile in place; undo it after each test."""
    snapshot = copy.deepcopy(fallback_data.fallback_profile)
    yield
    fallback_data.fallback_profile.clear()
    fallback_data.fallback_profile.update(snapshot)
