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
        cv.full_name = full_name.strip()
        cv.headline = headline.strip()
        cv.summary = summary.strip()
        cv.email = email.strip()
        cv.phone = phone.strip()
        cv.location = location.strip()
        cv.website = website.strip()
        cv.linkedin = linkedin.strip()
        cv.github = github.strip()
        cv.work_experience = work_exp
        cv.education = edu
        cv.skills = skl
        cv.certifications = certs
    else:
        cv = CV(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            full_name=full_name.strip(),
            headline=headline.strip(),
            summary=summary.strip(),
            email=email.strip(),
            phone=phone.strip(),
            location=location.strip(),
            website=website.strip(),
            linkedin=linkedin.strip(),
            github=github.strip(),
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