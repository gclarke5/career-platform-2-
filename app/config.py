from pydantic import ConfigDict, field_validator, model_validator
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
    # Fail closed: only an explicit ENVIRONMENT=development (set in the local .env) opens /admin
    # and allows the SQLite fallback. Servers that forget the variable stay in production.
    environment: str = "production"
    # Google Analytics 4 measurement ID. Empty (the default) leaves analytics and the consent
    # banner off entirely, so local development and tests never contact Google.
    ga_measurement_id: str = ""

    @field_validator("database_url")
    @classmethod
    def _use_psycopg_driver(cls, value: str) -> str:
        return normalize_database_url(value)

    @model_validator(mode="after")
    def _refuse_sqlite_outside_development(self) -> "Settings":
        # An empty SQLite file still answers SELECT 1, so /health would look healthy while the
        # site served no content. Off a laptop, a missing DATABASE_URL must stop startup instead.
        if self.environment != "development" and self.database_url.startswith("sqlite"):
            raise ValueError("DATABASE_URL must point at Postgres when ENVIRONMENT is not development")
        return self


settings = Settings()
