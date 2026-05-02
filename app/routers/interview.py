from fastapi import APIRouter, Request, Depends, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional
from db.session import get_db
from db.models import InterviewExperience
from auth.dependencies import get_optional_user

templates = Jinja2Templates(directory="templates")

router = APIRouter(prefix="/interviews", tags=["interviews"])

DIFFICULTY_LEVELS = ["Easy", "Medium", "Hard", "Very Hard"]
OUTCOMES = ["Got the job", "Rejected", "Withdrew", "Pending", "No response"]


@router.get("/")
async def interviews_list(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_optional_user),
):
    experiences = db.query(InterviewExperience).order_by(
        InterviewExperience.created_at.desc()
    ).all()

    return templates.TemplateResponse(
        request=request,
        name="interviews/index.html",
        context={"user": current_user, "experiences": experiences}
    )


@router.get("/new")
async def new_interview(
    request: Request,
    current_user=Depends(get_optional_user),
):
    if not current_user:
        return RedirectResponse(url="/auth/login")
    return templates.TemplateResponse(
        request=request,
        name="interview/new.html",
        context={
            "user": current_user,
            "difficulty_levels": DIFFICULTY_LEVELS,
            "outcomes": OUTCOMES,
        }
    )


@router.post("/new")
async def create_interview(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_optional_user),
    company: str = Form(...),
    role: str = Form(...),
    difficulty: Optional[str] = Form(None),
    outcome: Optional[str] = Form(None),
    questions: Optional[str] = Form(None),
    body: str = Form(...),
):
    if not current_user:
        return RedirectResponse(url="/auth/login")
    
    experience = InterviewExperience(
        user_id=current_user.id,
        company=company,
        role=role,
        difficulty=difficulty,
        outcome=outcome,
        questions=questions,
        body=body,
    )
    db.add(experience)
    db.commit()
    return RedirectResponse(url=f"/interviews/{experience.id}", status_code=303)


@router.get("/{experience_id}")
async def view_interview(
    experience_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_optional_user),
):
    experience = db.query(InterviewExperience).filter(
        InterviewExperience.id == experience_id
    ).first()
    if not experience:
        return RedirectResponse(url="/interviews")
    
    return templates.TemplateResponse(
        request=request,
        name="interviews/view.html",
        context={"user": current_user, "experience": experience}
    )