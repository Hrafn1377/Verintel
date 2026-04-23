from fastapi import APIRouter, Request, Depends, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from db.session import get_db
from db.models import User, Profile
from auth.dependencies import get_current_user, get_optional_user
from utils import sanitize_text, sanitize_url
import json
from audit import log_action


templates = Jinja2Templates(directory="templates")

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("")
async def profile_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    profile = db.query(Profile).filter(
        Profile.user_id == current_user.id
    ).first()

    return templates.TemplateResponse(
        request=request,
        name="profile/profile.html",
        context={"user": current_user, "profile": profile}
    )


@router.post("/update")
async def update_profile(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    display_name: str = Form(""),
    headline: str = Form(""),
    bio: str = Form(""),
    location: str = Form(""),
    website: str = Form(""),
    github_username: str = Form(""),
):
    profile = db.query(Profile).filter(
        Profile.user_id == current_user.id
    ).first()

    if not profile:
        return RedirectResponse(url="/profile", status_code=302)
    
@router.get("/export")
async def export_data(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from db.models import CV, EmployerReview

    profile = db.query(Profile).filter(
        Profile.user_id == current_user.id
    ).first()

    cv = db.query(CV).filter(
        CV.user_id == current_user.id
    ).first()

    reviews = db.query(EmployerReview).filter(
        EmployerReview.user_id == current_user.id
    ).all()

    data = {
        "account": {
            "email": current_user.email,
            "created_at": str(current_user.created_at),
        },
        "profile": {
            "display_name": profile.display_name if profile else None,
            "headline": profile.headline if profile else None,
            "bio": profile.bio if profile else None,
            "location": profile.location if profile else None,
            "website": profile.website if profile else None,
            "github_username": profile.github_username if profile else None,
        },
        "cv": {
            "full_name": cv.full_name if cv else None,
            "headline": cv.headline if cv else None,
            "summary": cv.summary if cv else None,
            "work_experience": cv.work_experience if cv else [],
            "education": cv.education if cv else [],
            "skills": cv.skills if cv else [],
            "certifications": cv.certifications if cv else [],
        },
        "reviews": [
            {
                "company_name": r.company_name,
                "rating": r.rating,
                "title": r.title,
                "body": r.body,
                "created_at": str(r.created_at),
            }
            for r in reviews
        ]
    }

    return Response(
        content=json.dumps(data, indent=2),
        media_type="application/json",
        headers={"Content-Dispostion": "attachment; filename=verintel-data.json"}
    )


@router.post("/delete-account")
async def delete_account(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from db.models import CV, EmployerReview, TrustScore

    db.query(EmployerReview).filter(
        EmployerReview.user_id == current_user.id
    ).delete()

    db.query(CV).filter(
        CV.user_id == current_user.id
    ).delete()

    db.query(Profile).filter(
        Profile.user_id == current_user.id
    ).delete()

    db.query(User).filter(
        User.id == current_user.id
    ).delete()

    db.commit()

    resp = RedirectResponse(url="/", status_code=302)
    resp.delete_cookie("access_token")
    resp.delete_cookie("refresh_token")
    return resp
    
    profile.display_name = sanitize_text(display_name, 100) or profile.display_name
    profile.headline = sanitize_text(headline, 200)
    profile.bio = sanitize_text(bio, 2000)
    profile.location = sanitize_text(location, 200)
    profile.website = sanitize_url(website)

    if github_username.strip():
        profile.github_username = sanitize_text(github_username, 100)
        profile.github_prompted = True

    log_action(
        db,
        action="user.delete_account",
        user_id=current_user.id,
        ip_address=request.client.host,
    )

    db.commit()

    return RedirectResponse(url="/profile", status_code=302)    