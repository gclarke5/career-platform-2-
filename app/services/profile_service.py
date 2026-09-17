import logging
from typing import Any

from sqlalchemy.orm import Session

from app.fallback_data import fallback_profile
from app.repositories import DatabaseUnavailableError, read_profile_data

logger = logging.getLogger(__name__)


def get_profile_payload(db_session: Session | None = None) -> dict[str, Any]:
    if db_session is None:
        return fallback_profile.copy()

    try:
        profile = read_profile_data(db_session)
    except DatabaseUnavailableError:
        logger.warning("Database unavailable; serving fallback profile", exc_info=True)
        return fallback_profile.copy()

    return profile if profile is not None else fallback_profile.copy()
