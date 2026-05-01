from fastapi import APIRouter, Request, Depends, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional
from db.session import get_db
from db.models import Discussion, DiscussionReply
from auth.dependencies import get_optional_user

templates = Jinja2Templates(directory="templates")

router = APIRouter(prefix="/discussions", tags=["discussions"])

CATEGORIES = ["general", "job-advice", "interview-prep", "networking", "success-stories"]


@router.get("/")
async def discussions_list(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_optional_user),
    category: Optional[str] = None,
):
    query = db.query(Discussion)
    if category:
        query = query.filter(Discussion.category == category)
    discussions = query.order_by(Discussion.is_pinned.desc(), Discussion.created_at.desc()).all()

    return templates.TemplateResponse(
        request=request,
        name="discussions/index.html",
        context={
            "user": current_user,
            "discussions": discussions,
            "categories": CATEGORIES,
            "active_category": category,
        }
    )


@router.get("/new")
async def new_discussion(
    request: Request,
    current_user=Depends(get_optional_user),
):
    if not current_user:
        return RedirectResponse(url="/auth/login")
    return templates.TemplateResponse(
        request=request,
        name="discussions/new.html",
        context={"user": current_user, "categories": CATEGORIES}
    )


@router.post("/new")
async def create_discussion(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_optional_user),
    title: str = Form(...),
    body: str = Form(...),
    category: str = ("general"),
):
    if not current_user:
        return RedirectResponse(url="/auth/login")
    
    discussion = Discussion(
        user_id=current_user.id,
        title=title,
        body=body,
        category=category,
    )
    db.add(discussion)
    db.commit()
    return RedirectResponse(url=f"/discussions/{discussion.id}", status_code=303)


@router.get("/{discussion_id}")
async def view_discussion(
    discussion_id: str,
    request: Request, 
    db: Session = Depends(get_db),
    current_user=Depends(get_optional_user),
):
    discussion = db.query(Discussion).filter(Discussion.id == discussion_id).first()
    if not discussion:
        return RedirectResponse(url="/discussions")
    
    replies = db.query(DiscussionReply).filter(
        DiscussionReply.discussion.id == discussion_id
    ).order_by(DiscussionReply.created_at.asc()).all()

    return templates.TemplateResponse(
        request=request,
        name="discussions/view.html",
        context={
            "user": current_user,
            "discussion": discussion,
            "replies": replies,
        }
    )


@router.post("/{discussion_id}/reply")
async def add_reply(
    discussion_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_optional_user),
    body: str = Form(...),
):
    if not current_user:
        return RedirectResponse(url="/auth/login")
    
    discussion = db.query(Discussion).filter(Discussion.id == discussion_id).first()
    if not discussion:
        return RedirectResponse(url="/discussions")
    
    reply = DiscussionReply(
        discussion_id=discussion_id,
        user_id=current_user.id,
        body=body,
    )
    db.add(reply)
    db.commit()
    return RedirectResponse(url=f"/discussions/{discussion_id}", status_code=303)