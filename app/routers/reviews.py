from fastapi import APIRouter, Request, Depends, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
import uuid
from db.session import get_db
from db.models import EmployerReview, User
from auth.dependencies import get_current_user, get_optional_user

templates = Jinja2Templates(directory="templates")

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.get("")
async def reviews_page(
    request: Request,
    company: Optional[str] = None,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    query =db.query(EmployerReview).filter(EmployerReview.flagged == False)

    if company:
        query = query.filter(
            EmployerReview.company_name.ilike(f"%{company}%")
        )

    reviews = query.order_by(EmployerReview.created_at.desc()).limit(50).all()

    return templates.TemplateResponse(
        request=request,
        name="reviews/index.html",
        context={"user": current_user, "reviews": reviews, "company": company}
    )


@router.get("/new")
async def new_review_page(
    request: Request,
    company: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    return templates.TemplateResponse(
        request=request,
        name="reviews/new.html",
        context={"user": current_user, "company": company}
    )


@router.post("/new")
async def create_review(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    company_name: str = Form(...),
    company_domain: str = Form(...),
    rating: float = Form(...),
    title: str = Form(...),
    body: str = Form(...),
    role: str = Form(""),
    employment_status: str = Form(""),
    pros: str = Form(""),
    cons: str = Form(""),
):
    review = EmployerReview(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        company_name=company_name.strip(),
        company_domain=company_domain.strip() or None,
        rating=max(1.0, min(5.0, rating)),
        title=title.strip(),
        body=body.strip(),
        role=role.strip() or None,
        employment_status=employment_status.strip() or None,
        pros=pros.strip() or None,
        cons=cons.strip() or None,
    )
    db.add(review)
    db.commit()

    return RedirectResponse(
        url=f"/reviews?company={company_name}",
        status_code=302
    )


@router.get("/company/{company_name}")
async def company_reviews(
    company_name: str,
    request: Request,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    reviews = db.query(EmployerReview).filter(
        EmployerReview.company_name.ilike(f"%{company_name}%"),
        EmployerReview.flagged == False
    ).order_by(EmployerReview.created_at.desc()).all()

    avg_rating = db.query(func.avg(EmployerReview.rating)).filter(
        EmployerReview.company_name.ilike(f"%{company_name}%"),
        EmployerReview.flagged == False
    ).scalar()

    return templates.TemplateResponse(
        request=request,
        name="reviews/company.html",
        context={
            "user": current_user,
            "reviews": reviews,
            "company_name": company_name,
            "avg_rating": round(avg_rating, 1) if avg_rating else None
        }
    )