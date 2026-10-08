from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import Education, Experience, Profile, Project, SiteMeta, Skill, VolunteerWork


class DatabaseUnavailableError(RuntimeError):
    """Raised when a profile read cannot be completed from the database."""


def read_profile_data(db: Session) -> dict[str, str | dict[str, str]] | None:
    try:
        profile = db.scalar(select(Profile).order_by(Profile.id).limit(1))
    except SQLAlchemyError as exc:
        raise DatabaseUnavailableError("Profile database read failed") from exc

    if profile is None:
        return None

    return {
        "full_name": profile.full_name,
        "headline": profile.headline,
        "summary": profile.summary,
        "email": profile.email,
        "linkedin_url": profile.linkedin_url,
        "github_url": profile.github_url,
        "location": profile.location,
        "cta_primary": profile.cta_primary,
        "contact": {
            "email": profile.email,
            "linkedin": profile.linkedin_url,
            "github": profile.github_url,
        },
    }


def _read_rows(db: Session, model: type) -> list:
    try:
        return list(db.scalars(select(model).order_by(model.id)))
    except SQLAlchemyError as exc:
        db.rollback()
        raise DatabaseUnavailableError(f"{model.__tablename__} database read failed") from exc


def _lines(value: str | None) -> list[str]:
    return [line.strip() for line in (value or "").splitlines() if line.strip()]


def _date_range(start: str | None, end: str | None) -> str:
    return " - ".join(part for part in (start, end) if part)


def read_experiences(db: Session) -> list[dict]:
    return [
        {
            "title": row.title,
            "company": row.company,
            "date_range": _date_range(row.start_date, row.end_date),
            "summary": row.summary,
            "highlights": _lines(row.highlights),
        }
        for row in _read_rows(db, Experience)
    ]


def read_projects(db: Session) -> list[dict]:
    return [
        {
            "title": row.title,
            "slug": row.slug,
            "short_summary": row.short_summary,
            "description_points": _lines(row.description),
            "metrics": row.metrics,
            "tools": row.tools,
            "category": row.category,
            "link_url": row.link_url,
            "case_study_url": row.case_study_url,
        }
        for row in _read_rows(db, Project)
    ]


def read_skills(db: Session) -> list[dict]:
    return [{"name": row.name, "category": row.category} for row in _read_rows(db, Skill)]


def read_education(db: Session) -> list[dict]:
    return [
        {"school": row.school, "degree": row.degree, "details": row.details}
        for row in _read_rows(db, Education)
    ]


def read_volunteer_work(db: Session) -> list[dict]:
    return [
        {
            "role": row.role,
            "organization": row.organization,
            "date_range": _date_range(row.start_date, row.end_date),
            "summary": row.summary,
        }
        for row in _read_rows(db, VolunteerWork)
    ]


def read_site_meta(db: Session) -> dict[str, str]:
    return {row.key: row.value for row in _read_rows(db, SiteMeta)}
