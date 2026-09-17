from sqlalchemy.orm import Session

from app.fallback_data import fallback_profile
from app.models import Profile, Project


def seed_database(db: Session) -> None:
    if db.query(Profile).first() is None:
        db.add(
            Profile(
                full_name=fallback_profile["full_name"],
                headline=fallback_profile["headline"],
                summary=fallback_profile["summary"],
                email=fallback_profile["email"],
                linkedin_url=fallback_profile["linkedin_url"],
                github_url=fallback_profile["github_url"],
                location=fallback_profile["location"],
                cta_primary=fallback_profile["cta_primary"],
            )
        )
    db.commit()
