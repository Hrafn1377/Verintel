from fastapi import APIRouter, Request, Depends, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional
from db.session import get_db
from db.models import Employer, EmployerJobPosting
from auth.dependencies import get_optional_user

templates = Jinja2Templates(directory="templates")

router = APIRouter(prefix="/employer", tags=["employer"])


@router.get("/register")
async def employer_register(request: Request, current_user=Depends(get_optional_user)):
    if not current_user:
        return RedirectResponse(url="/auth/login")
    return templates.TemplateResponse(
        request=request,
        name="employer/register.html",
        context={"user", current_user}
    )


@router.post("/register")
async def employer_register_submit(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_optional_user),
    company_name: str = Form(...),
    company_domain: str = Form(...),
    company_phone: Optional[str] = Form(None),
    company_country: str = Form("us"),
):
    if not current_user:
        return RedirectResponse(url="/auth/login")
    
    existing = db.query(Employer).filter(Employer.user_id == current_user.id).first()
    if existing:
        return RedirectResponse(url="/employer/dashboard")
    
    employer = Employer(
        user_id=current_user.id,
        compant_name=company_name,
        company_domain=company_domain,
        company_phone=company_phone,
        company_country=company_country,
    )
    db.add(employer)
    db.commit()
    return RedirectResponse(url="/employer/dashboard", status_code=303)


@router.get("/dashboard")
async def employer_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_optional_user),
):
    if not current_user:
        return RedirectResponse(url="/auth/login")
    
    employer = db.query(Employer).filter(Employer.user_id == current_user.id).first()
    if not employer:
        return RedirectResponse(url="/employer/register")
    
    postings = db.query(EmployerJobPosting).filter(
        EmployerJobPosting.employer_id == employer.id
    ).order_by(EmployerJobPosting.created_at.desc()).all()

    return templates.TemplateResponse(
        request=request,
        name="employer/dashboard.html",
        context={
            "user": current_user,
            "employer": employer,
            "postings": postings,
        }
    )


@router.get("/post-job")
async def post_job(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_optional_user),
):
    if not current_user:
        return RedirectResponse(url="/auth/login")
    
    employer = db.query(Employer).filter(Employer.user_id == current_user.id).first()
    if not employer:
        return RedirectResponse("/employer/register")
    
    return templates.TemplateResponse(
        request=request,
        name="employer/post_job.html",
        context={"user": current_user, "employer": employer}
    )


@router.post("/post-job")
async def post_job_submit(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_optional_user),
    title: str = Form(...),
    description: str = Form(...),
    location: Optional[str] = Form(None),
    salary_min: Optional[float] = Form(None),
    salary_max: Optional[float] = Form(None),
    job_type: Optional[str] = Form(None),
):
    if not current_user:
        return RedirectResponse(url="/auth/login")
    
    employer = db.query(Employer).filter(Employer.user_id == current_user.id).first()
    if not employer:
        return RedirectResponse(url="/employer.register")
    
    posting = EmployerJobPosting(
        employer_id=employer.id,
        title=title,
        description=description,
        location=location,
        salary_min=salary_min,
        salary_max=salary_max,
        job_type=job_type,
    )
    db.add(posting)
    db.commit()
    return RedirectResponse(url="/employer/dashboard", status_code=303)