from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from db.session import get_db
from db.models import UserFollow, User, Profile
from auth.dependencies import get_optional_user

templates = Jinja2Templates(directory="templates")

router = APIRouter(prefix="/network", tags=["network"])


@router.get("/")
async def netowrk_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_optional_user),
):
    if not current_user:
        return RedirectResponse(url="/auth/login")
    
    following = db.query(UserFollow).filter(
        UserFollow.follower_id == current_user.id
    ).all()

    followers = db.query(UserFollow).filter(
        UserFollow.following_id == current_user.id
    ).all()

    following_ids = [f.following_id for f in following]
    feed_users = db.query(User).filter(User.id.in_(following_ids)).all()

    return templates.TemplateResponse(
        request=request,
        name="network/index.html",
        context={
            "user": current_user,
            "following": following,
            "followers": followers,
            "feed_users": feed_users,
        }
    )


@router.post("/follow/{user_id}")
async def follow_user(
    user_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_optional_user),
):
    if not current_user:
        return RedirectResponse(url="/auth/login")
    
    if user_id == current_user.id:
        return RedirectResponse(url="/network/people")
    
    existing = db.query(UserFollow).filter(
        UserFollow.follower_id == current_user.id,
        UserFollow.following_id == user_id
    ).first()

    if not existing: 
        follow = UserFollow(
            follower_id=current_user.id,
            following_id=user_id
        )
        db.add(follow)
        db.commit()

    return RedirectResponse(url="/network/people", status_code=303)


@router.post("/unfollow/{user_id}")
async def unfollow_user(
    user_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_optional_user),
):
    if not current_user:
        return RedirectResponse(url="/auth/login")
    
    follow = db.query(UserFollow).filter(
        UserFollow.follower_id == current_user.id,
        UserFollow.following_id == user_id
    ).first()

    if follow:
        db.delete(follow)
        db.commit()

    return RedirectResponse(url="/network/people", status_code=303)