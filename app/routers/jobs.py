from fastapi import APIRouter, Request, Depends, Query
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional
from db.session import get_db
from db.models import JobPosting, TrustScore

templates = Jinja2Templates(directory="templates")

router = APIRouter(prefix="/jobs", tags=["jobs"])


def get_job_display(job: JobPosting, score: Optional[TrustScore]) -> dict:
    signals = score.signals if score else []
    overall_score = score.overall_score if score else 0.0

    if overall_score >= 0.7:
        verdict = "pass"
    elif overall_score >= 0.4:
        verdict = "warn"
    else:
        verdict = "fail"

    return {
        "id": job.id,
        "title": job.title,
        "company_name": job.company_id,
        "domain": "",
        "claimed_country": "us",
        "overall_score": overall_score,
        "verdict": verdict,
        "signals": signals,
        "summary": score.summary if score else "Not yet scored.",
    }


@router.get("")
async def jobs_page(
    request: Request,
    db: Session = Depends(get_db),
    q: str = Query(default=""),
    country: str = Query(default=""),
    verdict: str = Query(default=""),
):
    query = db.query(JobPosting)

    if q:
        query = query.filter(
            or_(
                JobPosting.title.ilike(f"%{q}%"),
            )
        )

    jobs_raw = query.limit(50).all()

    jobs = []
    for job in jobs_raw:
        score = db.query(TrustScore).filter(
            TrustScore.entity_id == job.id
        ).order_by(TrustScore.created_at.desc()).first()

        display = get_job_display(job, score)

        if verdict and display["verdict"] != verdict:
            continue

        jobs.append(display)

    is_htmx = request.headers.get("HX-Request")

    if is_htmx:
        return templates.TemplateResponse(
            request=request,
            name="partials/jobs_list.html",
            context={"jobs": jobs}
        )

    return templates.TemplateResponse(
        request=request,
        name="jobs.html",
        context={"jobs": jobs, "query": q, "country": country, "verdict": verdict}
    )


@router.get("/{job_id}")
async def job_detail(
    job_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    job = db.query(JobPosting).filter(JobPosting.id == job_id).first()

    if not job:
        return templates.TemplateResponse(
            request=request,
            name="404.html",
            status_code=404
        )

    score = db.query(TrustScore).filter(
        TrustScore.entity_id == job_id
    ).order_by(TrustScore.created_at.desc()).first()

    display = get_job_display(job, score)

    return templates.TemplateResponse(
        request=request,
        name="job.html",
        context={"job": display, "report": score}
    )