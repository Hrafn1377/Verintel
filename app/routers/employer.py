from fastapi import APIRouter, Request, Depends, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional
from db.session import get_db
from db.models import Employer, EmployerJobPosting
from auth.dependencies import get_optional_user
from scoring.engine import score_posting

templates = Jinja2Templates(directory="templates")

router = APIRouter(prefix="/employer", tags=["employer"])


@router.get("/register")
async def employer_register(request: Request, current_user=Depends(get_optional_user)):
    if not current_user:
        return RedirectResponse(url="/auth/login")
    return templates.TemplateResponse(
        request=request,
        name="employer/register.html",
        context={"user": current_user}
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
        company_name=company_name,
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
        return RedirectResponse(url="/employer/register")

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

    salary_text = ""
    if salary_min and salary_max:
        salary_text = f"Salary: ${salary_min:,.0f} - ${salary_max:,.0f} per year. "
    elif salary_min:
        salary_text = f"Salary: ${salary_min:,.0f} per year. "

    posting_text = f"{title}. {description} {salary_text}Location: {location or 'Not specified'}. Job type: {job_type or 'Not specified'}."

    try:
        report = await score_posting(
            posting_text=posting_text,
            company_name=employer.company_name,
            domain=employer.company_domain,
            claimed_country=employer.company_country or "us",
            phone=employer.company_phone,
            ip=request.client.host,
        )

        posting.verification_score = report.overall_score
        posting.verification_status = (
            "pass" if report.overall_score >= 0.6
            else "warn" if report.overall_score >= 0.4
            else "fail"
        )
        db.commit()
    except Exception:
        pass

    return RedirectResponse(url="/employer/dashboard", status_code=303)

@router.get("/posting/{posting_id}/edit")
async def edit_posting(
    posting_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_optional_user),
):
    if not current_user:
        return RedirectResponse(url="/auth/login")

    employer = db.query(Employer).filter(Employer.user_id == current_user.id).first()
    if not employer:
        return RedirectResponse(url="/employer/register")

    posting = db.query(EmployerJobPosting).filter(
        EmployerJobPosting.id == posting_id,
        EmployerJobPosting.employer_id == employer.id
    ).first()

    if not posting:
        return RedirectResponse(url="/employer/dashboard")

    return templates.TemplateResponse(
        request=request,
        name="employer/edit_posting.html",
        context={"user": current_user, "employer": employer, "posting": posting}
    )


@router.post("/posting/{posting_id}/edit")
async def edit_posting_submit(
    posting_id: str,
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
        return RedirectResponse(url="/employer/register")

    posting = db.query(EmployerJobPosting).filter(
        EmployerJobPosting.id == posting_id,
        EmployerJobPosting.employer_id == employer.id
    ).first()

    if not posting:
        return RedirectResponse(url="/employer/dashboard")

    posting.title = title
    posting.description = description
    posting.location = location
    posting.salary_min = salary_min
    posting.salary_max = salary_max
    posting.job_type = job_type
    posting.verification_status = None
    db.commit()
    return RedirectResponse(url="/employer/dashboard", status_code=303)


@router.post("/posting/{posting_id}/deactivate")
async def deactivate_posting(
    posting_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_optional_user),
):
    if not current_user:
        return RedirectResponse(url="/auth/login")

    employer = db.query(Employer).filter(Employer.user_id == current_user.id).first()
    if not employer:
        return RedirectResponse(url="/employer/register")

    posting = db.query(EmployerJobPosting).filter(
        EmployerJobPosting.id == posting_id,
        EmployerJobPosting.employer_id == employer.id
    ).first()

    if not posting:
        return RedirectResponse(url="/employer/dashboard")

    posting.is_active = not posting.is_active
    db.commit()
    return RedirectResponse(url="/employer/dashboard", status_code=303)