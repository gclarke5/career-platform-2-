from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db import get_db
from app.services.content_service import get_projects, get_resume_payload, get_site_meta
from app.services.profile_service import get_profile_payload

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def _page(request: Request, db: Session, template: str, **context):
    return templates.TemplateResponse(
        request,
        template,
        {"profile": get_profile_payload(db), "meta": get_site_meta(db), **context},
    )


@router.api_route("/", methods=["GET", "HEAD"], response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    return _page(request, db, "index.html", projects=get_projects(db))


@router.api_route("/resume", methods=["GET", "HEAD"], response_class=HTMLResponse)
def resume(request: Request, db: Session = Depends(get_db)):
    return _page(request, db, "resume.html", **get_resume_payload(db))


@router.api_route("/projects", methods=["GET", "HEAD"], response_class=HTMLResponse)
def projects(request: Request, db: Session = Depends(get_db)):
    return _page(request, db, "projects.html", projects=get_projects(db))


@router.api_route("/projects/{slug}", methods=["GET", "HEAD"], response_class=HTMLResponse)
def project_detail(request: Request, slug: str, db: Session = Depends(get_db)):
    all_projects = get_projects(db)
    index = next((i for i, item in enumerate(all_projects) if item["slug"] == slug), None)
    if index is None:
        raise HTTPException(status_code=404, detail="Project not found")
    next_project = all_projects[(index + 1) % len(all_projects)] if len(all_projects) > 1 else None
    return _page(request, db, "project_detail.html", project=all_projects[index], next_project=next_project)


@router.api_route("/contact", methods=["GET", "HEAD"], response_class=HTMLResponse)
def contact(request: Request, db: Session = Depends(get_db)):
    return _page(request, db, "contact.html")
