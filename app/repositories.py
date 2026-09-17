from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import Profile


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
