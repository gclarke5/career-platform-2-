from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env")

    app_name: str = "Career Platform"
    database_url: str = "sqlite:///./career_platform.db"
    railway_database_url: str | None = None
    environment: str = "development"


settings = Settings()
