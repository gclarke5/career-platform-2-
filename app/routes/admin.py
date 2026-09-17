from fastapi import APIRouter
from pydantic import BaseModel

from app.fallback_data import fallback_profile

router = APIRouter(prefix="/admin", tags=["admin"])


class ProfileUpdate(BaseModel):
    full_name: str
    headline: str
    summary: str
    email: str | None = None


@router.get("")
def admin_overview() -> dict[str, object]:
    return {"profile": fallback_profile, "message": "Admin data source is available."}


@router.put("/profile")
def update_profile(payload: ProfileUpdate) -> dict[str, object]:
    fallback_profile.update(payload.model_dump())
    fallback_profile["contact"]["email"] = payload.email
    return {"profile": fallback_profile}
