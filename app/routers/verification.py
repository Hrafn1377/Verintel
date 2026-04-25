from fastapi import APIRouter, Request, Depends, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
from db.session import get_db
from db.models import TrustScore
from scoring.engine import score_company, score_recruiter, score_posting
import uuid
from slowapi import Limiter
from slowapi.util import get_remote_address
from auth.dependencies import get_optional_user
from audit import log_action

templates = Jinja2Templates(directory="templates")

router = APIRouter(prefix="/verify", tags=["verification"])

limiter = Limiter(key_func=get_remote_address)


class CompanyRequest(BaseModel):
    company_name: str
    domain: str
    linkedin_slug: str | None = None
    claimed_country: str = "us"
    phone: str | None = None
    registered_name: str | None = None


class RecruiterRequest(BaseModel):
    recruiter_email: str
    company_domain: str
    claimed_country: str = "us"
    phone: str | None = None


class PostingRequest(BaseModel):
    posting_text: str
    company_name: str
    domain: str
    recruiter_email: str | None = None
    linkedin_slug: str | None = None
    indeed_job_id: str | None = None
    claimed_country: str = "us"
    phone: str | None = None


def persist_report(report, db: Session):
    record = TrustScore(
        id=str(uuid.uuid4()),
        entity_id=report.entity_id,
        entity_type=report.entity_type,
        overall_score=report.overall_score,
        signals=[
            {
                "label": s.label,
                "verdict": s.verdict,
                "weight": s.weight,
                "score": s.score,
                "reason": s.reason,
                "source": s.source,
            }
            for s in report.signals
        ],
        summary=report.summary,
    )
    db.add(record)
    db.commit()
    return record


@router.post("/company")
@limiter.limit("10/minute")
async def verify_company(
    payload: CompanyRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_optional_user),
):
    ip = request.client.host
    report = await score_company(
        company_name=payload.company_name,
        domain=payload.domain,
        linkedin_slug=payload.linkedin_slug,
        claimed_country=payload.claimed_country,
        phone=payload.phone,
        ip=ip,
        registered_name=payload.registered_name,
    )
    persist_report(report, db)
    log_action(
        db,
        action="verification.company",
        user_id=current_user.id if current_user else None,
        ip_address=request.client.host,
        resource=payload.company_name,
        details=f"score={report.overall_score:.2f} verdict={'pass' if report.overall_score >= 0.6 else 'warn' if report.overall_score >= 0.4 else 'fail'}",
    )
    return report


@router.post("/recruiter")
@limiter.limit("10/minute")
async def verify_recruiter(
    payload: RecruiterRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_optional_user),
):
    ip = request.client.host
    report = await score_recruiter(
        recruiter_email=payload.recruiter_email,
        company_domain=payload.company_domain,
        claimed_country=payload.claimed_country,
        phone=payload.phone,
        ip=ip,
    )
    persist_report(report, db)
    log_action(
        db,
        action="verification.recruiter",
        user_id=current_user.id if current_user else None,
        ip_address=request.client.host,
        resource=payload.recruiter_email,
        details=f"score={report.overall_score:.2f} verdict={'pass' if report.overall_score >= 0.6 else 'warn' if report.overall_score >= 0.4 else 'fail'}",
    )
    return report


@router.post("/posting")
@limiter.limit("10/minute")
async def verify_posting(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_optional_user),
    posting_text: str = Form(...),
    company_name: str = Form(...),
    domain: str = Form(...),
    recruiter_email: Optional[str] = Form(None),
    linkedin_slug: Optional[str] = Form(None),
    indeed_job_id: Optional[str] = Form(None),
    claimed_country: str = Form("us"),
    phone: Optional[str] = Form(None),
):
    ip = request.client.host
    report = await score_posting(
        posting_text=posting_text,
        company_name=company_name,
        domain=domain,
        recruiter_email=recruiter_email,
        linkedin_slug=linkedin_slug,
        indeed_job_id=indeed_job_id,
        claimed_country=claimed_country,
        phone=phone,
        ip=ip,
    )
    persist_report(report, db)
    log_action(
        db,
        action="verification.posting",
        user_id=current_user.id if current_user else None,
        ip_address=request.client.host,
        resource=company_name,
        details=f"score={report.overall_score:.2f} verdict={'pass' if report.overall_score >= 0.6 else 'warn' if report.overall_score >= 0.4 else 'fail'}",
    )
    return templates.TemplateResponse(
    request=request,
    name="partials/trust_report.html",
    context={"report": report}
)