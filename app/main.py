from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from routers.verification import router as verification_router
from routers.jobs import router as jobs_router
from db.session import Base, engine

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Verintel", version="0.1.0")

templates = Jinja2Templates(directory="templates")
templates.env.auto_reload = True

app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(verification_router)
app.include_router(jobs_router)


@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html"
    )