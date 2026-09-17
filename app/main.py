from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.config import settings
from app.db import engine
from app.routes.admin import router as admin_router
from app.routes.public import router as public_router


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name)
    app.mount("/static", StaticFiles(directory="static"), name="static")
    app.include_router(public_router)
    app.include_router(admin_router)

    @app.get("/health")
    def health() -> dict[str, str | bool]:
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except Exception:
            return {"status": "degraded", "database": "unavailable", "fallback": True}
        return {"status": "ok", "database": "healthy", "fallback": False}

    return app
