from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from routers.verification import router as verification_router
from routers.jobs import router as jobs_router
from db.session import Base, engine
from routers.auth import router as auth_router
from auth.dependencies import get_optional_user
from db.models import User
from routers.profile import router as profile_router
from routers.github import router as github_router
from routers.reviews import router as reviews_router
from routers.cv import router as cv_router

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


@app.get("/")
async def root(request: Request, current_user = Depends(get_optional_user)):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"user": current_user}
    )
