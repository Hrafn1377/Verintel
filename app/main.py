from fastapi import FastAPI, Request, Depends, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import Response as FastAPIResponse
from sqlalchemy.orm import Session
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from routers.verification import router as verification_router
from routers.jobs import router as jobs_router
from db.session import get_db, Base, engine
from routers.auth import router as auth_router
from auth.dependencies import get_optional_user
from db.models import User
from routers.profile import router as profile_router
from routers.github import router as github_router
from routers.reviews import router as reviews_router
from routers.discover import router as discover_router
from routers.cv import router as cv_router
from routers.employer import router as employer_router
from urllib.parse import quote

Base.metadata.create_all(bind=engine)

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="Verintel", version="0.1.0")

from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(self), camera=(), microphone=()"
        return response

app.add_middleware(SecurityHeadersMiddleware)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

templates = Jinja2Templates(directory="templates")
templates.env.auto_reload = True

app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(verification_router)
app.include_router(jobs_router)
app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(github_router)
app.include_router(reviews_router)
app.include_router(cv_router)
app.include_router(discover_router)
app.include_router(employer_router)


@app.get("/")
async def root(request: Request, current_user = Depends(get_optional_user)):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"user": current_user}
    )


@app.get("/help")
async def help_page(request: Request, current_user = Depends(get_optional_user)):
    return templates.TemplateResponse(
        request=request,
        name="help.html",
        context={"user": current_user}
    )

@app.get("/faq")
async def faq_page(request: Request, current_user = Depends(get_optional_user)):
    return templates.TemplateResponse(
        request=request,
        name="faq.html",
        context={"user": current_user}
    )

@app.get("/about")
async def about_page(request: Request, current_user = Depends(get_optional_user)):
    return templates.TemplateResponse(
        request=request,
        name="about.html",
        context={"user": current_user}
    )

@app.get("/privacy")
async def privacy_page(request: Request, current_user = Depends(get_optional_user)):
    return templates.TemplateResponse(
        request=request,
        name="privacy.html",
        context={"user": current_user}
    )

@app.get("/contact")
async def contact_page(request: Request, current_user = Depends(get_optional_user)):
    return templates.TemplateResponse(
        request=request,
        name="contact.html",
        context={"user": current_user}
    )

@app.post("/contact")
async def contact_submit(
    request: Request,
    db: Session = Depends(get_db),
    name: str = Form(...),
    email: str = Form(...),
    subject: str = Form(None),
    message: str = Form(...),
):
    from db.models import ContactSubmission
    submission = ContactSubmission(
        name=name,
        email=email,
        subject=subject,
        message=message,
    )
    db.add(submission)
    db.commit()
    return templates.TemplateResponse(
        request=request,
        name="contact.html",
        context={
            "user": None,
            "success": True,
        }
    )

@app.get("/terms")
async def terms_page(request: Request, current_user = Depends(get_optional_user)):
    return templates.TemplateResponse(
        request=request,
        name="terms.html",
        context={"user": current_user}
    )

@app.get("/hall-of-shame")
async def hall_of_shame_page(request: Request, current_user = Depends(get_optional_user)):
    return templates.TemplateResponse(
        request=request,
        name="hall_of_shame.html",
        context={"user": current_user}
    )

@app.get("/sitemap.xml")
async def sitemap(db: Session = Depends(get_db)):
    from db.models import JobPosting, EmployerReview

    pages = [
        "https://verintel.com",
        "https://verintel.com/jobs",
        "https://verintel.com/reviews",
        "https://verintel.com/about",
        "https://verintel.com/help",
        "https://verintel.com/faq",
        "https://verintel.com/contact",
        "https://verintel.com/privacy",
        "https://verintel.com/terms",
        "https://verintel.com/hall-of-shame",
    ]

    companies = db.query(EmployerReview.company_name).distinct().all()
    for (company_name,) in companies:
        pages.append(f"https://verintel.com/reviews/company/{quote(company_name)}")

    urls = "\n".join([
        f"""  <url>
    <loc>{page}</loc>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>""" for page in pages
    ])

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
  <urlset xmlns="http://www.sitemaps.org/schemas/sitemate/0.9">
  {urls}
  </urlset>"""

    return FastAPIResponse(content=xml, media_type="application/xml")  