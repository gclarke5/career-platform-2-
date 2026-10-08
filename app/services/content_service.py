import logging
from collections.abc import Callable
from typing import Any

from sqlalchemy.orm import Session

from app.fallback_data import fallback_experience, fallback_projects, fallback_site_meta
from app.repositories import (
    DatabaseUnavailableError,
    read_education,
    read_experiences,
    read_projects,
    read_site_meta,
    read_skills,
    read_volunteer_work,
)

logger = logging.getLogger(__name__)


def _read_or_fallback(db_session: Session, reader: Callable[[Session], list[dict]], fallback: list[dict]) -> list[dict]:
    try:
        return reader(db_session)
    except DatabaseUnavailableError:
        logger.warning("Database unavailable; serving fallback %s", reader.__name__, exc_info=True)
        return [item.copy() for item in fallback]


def get_experience(db_session: Session) -> list[dict]:
    return _read_or_fallback(db_session, read_experiences, fallback_experience)


def get_projects(db_session: Session) -> list[dict]:
    return _read_or_fallback(db_session, read_projects, fallback_projects)


def get_project(db_session: Session, slug: str) -> dict | None:
    return next((item for item in get_projects(db_session) if item["slug"] == slug), None)


def get_education(db_session: Session) -> list[dict]:
    return _read_or_fallback(db_session, read_education, [])


def get_volunteer_work(db_session: Session) -> list[dict]:
    return _read_or_fallback(db_session, read_volunteer_work, [])


def get_skill_groups(db_session: Session) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    for skill in _read_or_fallback(db_session, read_skills, []):
        groups.setdefault(skill["category"] or "Skills", []).append(skill["name"])
    return groups


def get_site_meta(db_session: Session | None) -> dict[str, Any]:
    try:
        meta = {**fallback_site_meta, **(read_site_meta(db_session) if db_session is not None else {})}
    except DatabaseUnavailableError:
        logger.warning("Database unavailable; serving fallback site meta", exc_info=True)
        meta = dict(fallback_site_meta)
    proof_points = []
    for line in meta.get("proof_points", "").splitlines():
        text, href, source = (line.split("|") + ["", ""])[:3]
        if text.strip():
            proof_points.append({"text": text.strip(), "href": href.strip(), "source": source.strip()})
    return {"availability": meta.get("availability", ""), "proof_points": proof_points}


def get_resume_payload(db_session: Session) -> dict[str, Any]:
    return {
        "experience": get_experience(db_session),
        "education": get_education(db_session),
        "skill_groups": get_skill_groups(db_session),
        "volunteer_work": get_volunteer_work(db_session),
    }
