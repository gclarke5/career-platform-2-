from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.fallback_data import fallback_experience, fallback_projects
from app.services.profile_service import get_profile_payload

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request, "index.html", {"profile": get_profile_payload()})


@router.get("/resume", response_class=HTMLResponse)
async def resume(request: Request):
    return templates.TemplateResponse(
        request,
        "resume.html",
        {"profile": get_profile_payload(), "experience": fallback_experience},
    )


@router.get("/projects", response_class=HTMLResponse)
async def projects(request: Request):
    return templates.TemplateResponse(
        request,
        "projects.html",
        {"projects": fallback_projects},
    )


@router.get("/projects/{slug}", response_class=HTMLResponse)
async def project_detail(request: Request, slug: str):
    project = next((item for item in fallback_projects if item["slug"] == slug), None)
    if project is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Project not found")
    return templates.TemplateResponse(request, "project_detail.html", {"project": project})


@router.get("/contact", response_class=HTMLResponse)
async def contact(request: Request):
    return templates.TemplateResponse(request, "contact.html", {"profile": get_profile_payload()})
