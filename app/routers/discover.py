from fastapi import APIRouter, Request, Depends, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional
import uuid
import json
from db.session import get_db
from db.models import JobPreferences, User, JobPosting
from auth.dependencies import get_current_user, get_optional_user
from utils import sanitize_text

templates = Jinja2Templates(directory="templates")

router = APIRouter(prefix="/discover", tags=["discover"])


@router.get("")
async def discover_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    preferences = db.query(JobPreferences).filter(
        JobPreferences.user_id == current_user.id
    ).first()

    jobs = []
    if preferences:
        jobs = get_matched_jobs(db, preferences)

    return templates.TemplateResponse(
        request=request,
        name="discover/index.html",
        context={
            "user": current_user,
            "preferences": preferences,
            "jobs": jobs
        }
    )


@router.get("/preferences")
async def preferences_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    preferences = db.query(JobPreferences).filter(
        JobPreferences.user_id == current_user.id
    ).first()

    return templates.TemplateResponse(
        request=request,
        name="discover/preferences.html",
        context={"user": current_user, "preferences": preferences}
    )


@router.post("/preferences")
async def save_preferences(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    job_titles: str = Form("[]"),
    locations: str = Form("[]"),
    remote_preference: str = Form(""),
    min_salary: str = Form(""),
    max_salary: str = Form(""),
    excluded_industries: str = Form("[]"),
    excluded_companies: str = Form("[]"),
    open_to_relocation: bool = Form(False),
):
    preferences = db.query(JobPreferences).filter(
        JobPreferences.user_id == current_user.id
    ).first()

    try:
        titles = json.loads(job_titles)
        locs = json.loads(locations)
        excl_ind = json.loads(excluded_industries)
        excl_comp = json.loads(excluded_companies)
    except json.JSONDecodeError:
        titles = []
        locs = []
        excl_ind = []
        excl_comp = []

    min_sal = float(min_salary) if min_salary.strip() else None
    max_sal = float(max_salary) if max_salary.strip() else None

    if preferences:
        preferences.job_titles = titles
        preferences.locations = locs
        preferences.remote_preference = remote_preference.strip() or None
        preferences.min_salary = min_sal
        preferences.max_salary = max_sal
        preferences.excluded_industries = excl_ind
        preferences.excluded_companies = excl_comp
        preferences.open_to_relocation = open_to_relocation
    else:
        preferences = JobPreferences(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            job_titles=titles,
            locations=locs,
            remote_preference=remote_preference.strip() or None,
            min_salary=min_sal,
            max_salary=max_sal,
            excluded_industries=excl_ind,
            excluded_companies=excl_comp,
            open_to_relocation=open_to_relocation,
        )
        db.add(preferences)

    db.commit()
    return RedirectResponse(url="/discover", status_code=302)


def get_matched_jobs(db: Session, preferences: JobPreferences):
    query = db.query(JobPosting)

    if preferences.job_titles:
        from sqlalchemy import or_
        title_filters = [
            JobPosting.title.ilike(f"%{title}%")
            for title in preferences.job_titles
        ]
        query = query.filter(or_(*title_filters))

    if preferences.excluded_companies:
        for company in preferences.excluded_companies:
            query = query.filter(
                ~JobPosting.company_name.ilike(f"%{company}%")
            )

    jobs = query.order_by(JobPosting.created_at.desc()).limit(20).all()
    return jobs