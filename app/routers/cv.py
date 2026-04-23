from fastapi import APIRouter, Request, Depends, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.orm import Session
from typing import Optional
import uuid
import json
from db.session import get_db
from db.models import CV, User
from auth.dependencies import get_current_user
from pathlib import Path
from utils import sanitize_text, sanitize_url

templates = Jinja2Templates(directory="templates")

router = APIRouter(prefix="/cv", tags=["cv"])


@router.get("")
async def cv_builder(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    cv = db.query(CV).filter(CV.user_id == current_user.id).first()

    return templates.TemplateResponse(
        request=request,
        name="cv/builder.html",
        context={"user": current_user, "cv": cv}
    )


@router.post("/save")
async def save_cv(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    full_name: str = Form(""),
    headline: str = Form(""),
    summary: str = Form(""),
    email: str = Form(""),
    phone: str = Form(""),
    location: str = Form(""),
    website: str = Form(""),
    linkedin: str = Form(""),
    github: str = Form(""),
    work_experience: str = Form("[]"),
    education: str = Form("[]"),
    skills: str = Form("[]"),
    certifications: str = Form("[]"),
):
    cv = db.query(CV).filter(CV.user_id == current_user.id).first()

    try:
        work_exp = json.loads(work_experience)
        edu = json.loads(education)
        skl = json.loads(skills)
        certs = json.loads(certifications)
    except json.JSONDecodeError:
        work_exp = []
        edu = []
        skl = []
        certs = []

    if cv:
        cv.full_name = sanitize_text(full_name, 200)
        cv.headline = sanitize_text(headline, 200)
        cv.summary = sanitize_text(summary, 2000)
        cv.email = sanitize_text(email, 200)
        cv.phone = sanitize_text(phone, 50)
        cv.location = sanitize_text(location, 200)
        cv.website = sanitize_url(website)
        cv.linkedin = sanitize_text(linkedin, 200)
        cv.github = sanitize_text(github, 100)
        cv.work_experience = work_exp
        cv.education = edu
        cv.skills = skl
        cv.certifications = certs
    else:
        cv = CV(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            full_name=sanitize_text(full_name, 200),
            headline=sanitize_text(headline, 200),
            summary=sanitize_text(summary, 2000),
            email=sanitize_text(email, 200),
            phone=sanitize_text(phone, 50),
            location=sanitize_text(location, 200),
            website=sanitize_url(website),
            linkedin=sanitize_text(linkedin, 200),
            github=sanitize_text(github, 100),
            work_experience=work_exp,
            education=edu,
            skills=skl,
            certifications=certs,
        )
        db.add(cv)

    db.commit()
    return RedirectResponse(url="/cv/preview", status_code=302)


@router.get("/preview")
async def cv_preview(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    cv = db.query(CV).filter(CV.user_id == current_user.id).first()

    if not cv:
        return RedirectResponse(url="/cv", status_code=302)
    
    return templates.TemplateResponse(
        request=request,
        name="cv/preview.html",
        context={"user": current_user, "cv": cv}
    )


@router.get("/download")
async def download_cv(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    cv = db.query(CV).filter(CV.user_id == current_user.id).first()

    if not cv:
        return RedirectResponse(url="/cv", status_code=302)
    
    from jinja2 import Environment, FileSystemLoader
    import weasyprint

    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("cv/preview.html")
    html_content = template.render(cv=cv, pdf_mode=True)

    pdf = weasyprint.HTML(string=html_content).write_pdf()

    filename = f"{cv.full_name or 'cv'}.pdf".replace(" ", "_")

    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )