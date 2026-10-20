import os

from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.db import engine
from app.routes.admin import router as admin_router
from app.routes.public import router as public_router
from app.routes.public import templates
from app.services.content_service import get_site_meta
from app.services.profile_service import get_profile_payload


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name)
    app.mount("/static", StaticFiles(directory="static"), name="static")
    app.include_router(public_router)
    # /admin is unauthenticated, so mount it only when explicitly in development and never on
    # Railway (which sets RAILWAY_ENVIRONMENT). A missing or mistyped ENVIRONMENT stays closed.
    if settings.environment == "development" and "RAILWAY_ENVIRONMENT" not in os.environ:
        app.include_router(admin_router)

    @app.exception_handler(StarletteHTTPException)
    async def not_found_page(request: Request, exc: StarletteHTTPException):
        # Visitors get a navigable page; API-style routes keep FastAPI's JSON errors.
        if exc.status_code != 404 or request.url.path.startswith(("/admin", "/health", "/static")):
            return await http_exception_handler(request, exc)
        return templates.TemplateResponse(
            request,
            "404.html",
            {"profile": get_profile_payload(None), "meta": get_site_meta(None)},
            status_code=404,
        )

    @app.api_route("/health", methods=["GET", "HEAD"])
    def health() -> dict[str, str | bool]:
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except Exception:
            return {"status": "degraded", "database": "unavailable", "fallback": True}
        return {"status": "ok", "database": "healthy", "fallback": False}

    return app
