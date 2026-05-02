from fastapi import APIRouter, Request, Depends, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional
from db.session import get_db
from db.models import SuccessStory
from auth.dependencies import get_optional_user

templates = Jinja2Templates(directory="templates")

router = APIRouter(prefix="/success-stories", tags=["success_stories"])


@router.get("/")
async def success_stories_list(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_optional_user),
):
    stories = db.query(SuccessStory).order_by(SuccessStory.created_at.desc()).all()

    return templates.TemplateResponse(
        request=request,
        name="success_stories/index.html",
        context={"user": current_user, "stories": stories}
    )


@router.get("/new")
async def new_story(
    request: Request,
    current_user=Depends(get_optional_user),
):
    if not current_user:
        return RedirectResponse(url="/auth/login")
    return templates.TemplateResponse(
        request=request,
        name="success_stories/new.html",
        context={"user": current_user}
    )


@router.post("/new")
async def create_story(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_optional_user),
    title: str = Form(...),
    body: str = Form(...),
    company: Optional[str] = Form(None),
    role: Optional[str] = Form(None,)
):
    if not current_user:
        return RedirectResponse(url="/auth/login")
    
    story = SuccessStory(
        user_id=current_user.id,
        title=title,
        body=body,
        company=company,
        role=role,
    )
    db.add(story)
    db.commit()
    return RedirectResponse(url=f"/success-stories/{story.id}", status_code=303)


@router.get("/{story_id}")
async def view_story(
    story_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_optional_user),
):
    story = db.query(SuccessStory).filter(SuccessStory.id == story_id).first()
    if not story:
        return RedirectResponse(url="/success-stories")
    
    return templates.TemplateResponse(
        request=request,
        name="success_stories/view.html",
        context={"user": current_user, "story": story}
    )