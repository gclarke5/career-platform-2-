from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db import get_db
from app.services.content_service import get_project, get_projects, get_resume_payload
from app.services.profile_service import get_profile_payload

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(request, "index.html", {"profile": get_profile_payload(db)})


@router.get("/resume", response_class=HTMLResponse)
async def resume(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        request,
        "resume.html",
        {"profile": get_profile_payload(db), **get_resume_payload(db)},
    )


@router.get("/projects", response_class=HTMLResponse)
async def projects(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        request,
        "projects.html",
        {"profile": get_profile_payload(db), "projects": get_projects(db)},
    )


@router.get("/projects/{slug}", response_class=HTMLResponse)
async def project_detail(request: Request, slug: str, db: Session = Depends(get_db)):
    project = get_project(db, slug)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return templates.TemplateResponse(
        request,
        "project_detail.html",
        {"profile": get_profile_payload(db), "project": project},
    )


@router.get("/contact", response_class=HTMLResponse)
async def contact(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(request, "contact.html", {"profile": get_profile_payload(db)})
