from fastapi import APIRouter, Request, Depends, Form, Response, HTTPException, status
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional
import uuid
from slowapi import Limiter
from slowapi.util import get_remote_address
from db.session import get_db
from db.models import User, Profile
from auth.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token
)
from fastapi.responses import RedirectResponse

limiter = Limiter(key_func=get_remote_address)

templates = Jinja2Templates(directory="templates")

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/register")
async def register_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="auth/register.html"
    )


@router.post("/register")
@limiter.limit("3/minute")
async def register(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    email: str = Form(...),
    password: str = Form(...),
    display_name: str = Form(...),
):
    existing = db.query(User).filter(User.email == email.lower().strip()).first()
    if existing:
        return templates.TemplateResponse(
            request=request,
            name="auth/register.html",
            context={"error": "An account with that email already exists."}
        )
    
    user = User(
        id=str(uuid.uuid4()),
        email=email.lower().strip(),
        hashed_password=hash_password(password),
        is_active=True,
        is_verified=False,
    )
    db.add(user)
    db.flush()

    profile = Profile(
        id=str(uuid.uuid4()),
        user_id=user.id,
        display_name=display_name.strip(),
    )
    db.add(profile)
    db.commit()

    access_token = create_access_token(data={"sub": user.id})
    refresh_token = create_refresh_token(data={"sub": user.id})

   
    resp = RedirectResponse(url="/", status_code=302)
    resp.set_cookie("access_token", access_token, httponly=True, samesite="lax")
    resp.set_cookie("refresh_token", refresh_token, httponly=True, samesite="lax")
    return resp


@router.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="auth/login.html"
    )


@router.post("/login")
@limiter.limit("5/minute")
async def login(
    request: Request,
    db: Session = Depends(get_db),
    email: str = Form(...),
    password: str = Form(...),
):
    user = db.query(User).filter(User.email == email.lower().strip()).first()
           
    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            request=request,
            name="auth/login.html",
            context={"error": "Invalid email or password"}
        )
    
    access_token = create_access_token(data={"sub": user.id})
    refresh_token = create_refresh_token(data={"sub": user.id})

    resp = RedirectResponse(url="/", status_code=302)
    resp.set_cookie("access_token", access_token, httponly=True, samesite="lax")
    resp.set_cookie("refresh_token", refresh_token, httponly=True, samesite="lax")
    return resp


@router.post("/logout")
async def logout(request: Request):
    resp = templates.TemplateResponse(
        request=request,
        name="auth/login.html",
        context={"success": "You have been logged out."}
    )
    resp.delete_cookie("access_token")
    resp.delete_cookie("refresh_token")
    return resp


@router.get("/refresh")
async def refresh_token(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("refresh_token")

    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    
    payload = decode_token(token)

    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    
    access_token = create_access_token(data={"sub": user.id})

    resp = Response()
    resp.set_cookie("access_token", access_token, httponly=True, samesite="lax")
    return resp
    