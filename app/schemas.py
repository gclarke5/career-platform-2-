from pydantic import BaseModel, ConfigDict


class ProfileCreate(BaseModel):
    full_name: str
    headline: str
    summary: str
    email: str | None = None
    linkedin_url: str | None = None
    github_url: str | None = None
    location: str | None = None
    cta_primary: str | None = None


class ProfileRead(ProfileCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
