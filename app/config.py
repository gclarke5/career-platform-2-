from pydantic import ConfigDict, field_validator
from pydantic_settings import BaseSettings


def normalize_database_url(url: str) -> str:
    """Point bare Postgres URLs (the form Railway provides) at the psycopg 3 driver."""
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env")

    app_name: str = "Career Platform"
    database_url: str = "sqlite:///./career_platform.db"
    railway_database_url: str | None = None
    environment: str = "development"

    @field_validator("database_url")
    @classmethod
    def _use_psycopg_driver(cls, value: str) -> str:
        return normalize_database_url(value)


settings = Settings()
