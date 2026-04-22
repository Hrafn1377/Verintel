from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from routers.verification import router as verification_router
from routers.jobs import router as jobs_router
from db.session import Base, engine
from routers.auth import router as auth_router
from auth.dependencies import get_optional_user
from db.models import User
from routers.profile import router as profile_router
from routers.github import router as github_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Verintel", version="0.1.0")

templates = Jinja2Templates(directory="templates")
templates.env.auto_reload = True

app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(verification_router)
app.include_router(jobs_router)
app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(github_router)


@app.get("/")
async def root(request: Request, current_user = Depends(get_optional_user)):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"user": current_user}
    )