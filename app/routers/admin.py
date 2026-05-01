from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from db.session import get_db
from db.models import ContactSubmission, EmployerJobPosting, Employer, User
from auth.dependencies import get_optional_user

templates = Jinja2Templates(directory="templates")

router = APIRouter(prefix="/admin", tags=["admin"])


def require_admin(current_user):
    if not current_user:
        return False
    return current_user.email == "hrafn@joinverintel.com"


@router.get("/")
async def admin_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_optional_user),
):
    if not require_admin(current_user):
        return RedirectResponse(url="/")
    
    total_users = db.query(User).count()
    total_employers = db.query(Employer).count()
    total_postings = db.query(EmployerJobPosting).count()
    flagged_postings = db.query(EmployerJobPosting).filter(
        EmployerJobPosting.verification_status == "fail"
    ).count()
    unread_contacts = db.query(ContactSubmission).filter(
        ContactSubmission.is_read == False
    ).count()

    return templates.TemplateResponse(
        request=request,
        name="admin/dashboard.html",
        context={
            "user": current_user,
            "total_users": total_users,
            "total_employers": total_employers,
            "total_postings": total_postings,
            "flagged_postings": flagged_postings,
            "unread_contacts": unread_contacts,
        }
    )


@router.get("/contacts")
async def admin_contacts(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_optional_user),
):
    if not require_admin(current_user):
        return RedirectResponse(url="/")
    
    submissions = db.query(ContactSubmission).order_by(
        ContactSubmission.created_at.desc()
    ).all()

    return templates.TemplateResponse(
        request=request,
        name="admin/contacts.html",
        context={"user": current_user, "submissions": submissions}
    )


@router.post("/contacts/{submission_id}/read")
async def mark_contact_read(
    submission_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_optional_user,)
):
    if not require_admin(current_user):
        return RedirectResponse(url="/")
    
    submission = db.query(ContactSubmission).filter(
        ContactSubmission.id == submission_id
    ).first()

    if submission:
        submission.is_read = True
        db.commit()

    return RedirectResponse(url="/admin/contacts", status_code=303)


@router.get("/postings")
async def admin_postings(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_optional_user,)
):
    if not require_admin(current_user):
        return RedirectResponse(url="/")
    
    postings = db.query(EmployerJobPosting).order_by(
        EmployerJobPosting.created_at.desc()
    ).all()

    return templates.TemplateResponse(
        request=request,
        name="admin/postings.html",
        context={"user": current_user, "postings": postings}
    )


@router.get("/employers")
async def admin_employers(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_optional_user),
):
    if not require_admin(current_user):
        return RedirectResponse(url="/")
    
    employers = db.query(Employer).order_by(
        Employer.created_at.desc()
    ).all()

    return templates.TemplateResponse(
        request=request,
        name="admin/employers.html",
        context={"user": current_user, "employers": employers}
    )