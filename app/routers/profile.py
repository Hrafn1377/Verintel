from fastapi import APIRouter, Request, Depends, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from db.session import get_db
from db.models import User, Profile
from auth.dependencies import get_current_user, get_optional_user

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
    
    profile.display_name = display_name.strip() or profile.display_name
    profile.headline = headline.strip()
    profile.bio = bio.strip()
    profile.location = location.strip()
    profile.website = website.strip()

    if github_username.strip():
        profile.github_username = github_username.strip()
        profile.github_prompted = True

    db.commit()

    return RedirectResponse(url="/profile", status_code=302)    