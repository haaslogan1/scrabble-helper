from __future__ import annotations

import logging
from typing import Any

from authlib.integrations.starlette_client import OAuth
from fastapi import HTTPException, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.responses import RedirectResponse

from app.config import settings
from app.email_validation import validate_email
from app.friends import assign_default_username
from app.models import User
from app.passwords import hash_password, validate_password_policy, verify_password

logger = logging.getLogger(__name__)

oauth = OAuth()
oauth.register(
    name="google",
    client_id=settings.google_client_id,
    client_secret=settings.google_client_secret,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


def get_or_create_user(db: Session, *, email: str, name: str, provider_sub: str) -> User:
    user = (
        db.query(User)
        .filter(User.provider == "google", User.provider_sub == provider_sub)
        .one_or_none()
    )
    if user:
        if user.email != email or user.name != name:
            user.email = email
            user.name = name
            db.commit()
            db.refresh(user)
        if not user.username:
            assign_default_username(db, user)
        return user

    existing = db.query(User).filter(User.email == email).one_or_none()
    if existing:
        existing.provider = "google"
        existing.provider_sub = provider_sub
        existing.name = name
        db.commit()
        db.refresh(existing)
        if not existing.username:
            assign_default_username(db, existing)
        return existing

    user = User(email=email, name=name, provider="google", provider_sub=provider_sub)
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="An account with this email already exists. Try signing in with email instead.",
        ) from exc
    assign_default_username(db, user)
    return user


def get_current_user(request: Request, db: Session) -> User:
    if settings.dev_auth_bypass:
        user = db.query(User).filter(User.email == settings.dev_user_email).one_or_none()
        if user is None:
            user = User(
                email=settings.dev_user_email,
                name=settings.dev_user_name,
                provider="dev",
                provider_sub="dev-local",
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        request.session["user_id"] = user.id
        return user

    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def require_admin(request: Request, db: Session) -> User:
    user = get_current_user(request, db)
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


def register_basic_user(
    db: Session, request: Request, *, email: str, password: str, name: str
) -> User:
    try:
        email = validate_email(email)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    existing = db.query(User).filter(User.email == email).one_or_none()
    if existing:
        raise HTTPException(
            status_code=409,
            detail="An account with this email already exists. Try signing in instead.",
        )
    try:
        validate_password_policy(password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    user = User(
        email=email,
        name=name.strip() or email.split("@")[0],
        provider="local",
        provider_sub=email,
        password_hash=hash_password(password),
        is_admin=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    assign_default_username(db, user)
    request.session["user_id"] = user.id
    return user


def login_basic_user(db: Session, request: Request, *, email: str, password: str) -> User:
    try:
        email = validate_email(email)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    user = db.query(User).filter(User.email == email).one_or_none()
    if user is None or not user.password_hash:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    request.session["user_id"] = user.id
    return user


def bootstrap_admin(db: Session) -> None:
    if not settings.admin_email or not settings.admin_password:
        return
    email = settings.admin_email.strip().lower()
    user = db.query(User).filter(User.email == email).one_or_none()
    if user is None:
        user = User(
            email=email,
            name="Admin",
            provider="local",
            provider_sub=email,
            password_hash=hash_password(settings.admin_password),
            is_admin=True,
        )
        db.add(user)
    else:
        user.is_admin = True
        user.password_hash = hash_password(settings.admin_password)
        if user.provider in ("dev", "local"):
            user.provider = "local"
            user.provider_sub = email
    db.commit()
    logger.info("Admin user ensured for %s", email)


async def google_login(request: Request) -> RedirectResponse:
    if settings.dev_auth_bypass:
        return RedirectResponse(url=f"{settings.frontend_url}/auth/dev-login")
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(status_code=503, detail="Google sign-in is not configured")
    redirect_uri = f"{settings.base_url}/auth/callback/google"
    return await oauth.google.authorize_redirect(request, redirect_uri)


def dev_login(request: Request, db: Session) -> RedirectResponse:
    if not settings.dev_auth_bypass:
        raise HTTPException(status_code=404, detail="Not found")
    user = db.query(User).filter(User.email == settings.dev_user_email).one_or_none()
    if user is None:
        user = User(
            email=settings.dev_user_email,
            name=settings.dev_user_name,
            provider="dev",
            provider_sub="dev-local",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    request.session["user_id"] = user.id
    return RedirectResponse(url=settings.frontend_url or "/")


def auth_config() -> dict[str, bool]:
    return {
        "google_login_enabled": bool(settings.google_client_id and settings.google_client_secret),
        "dev_login_enabled": settings.dev_auth_bypass,
        "local_auth_enabled": settings.local_auth_enabled,
        "email_verification_enabled": settings.email_verification_enabled,
    }


async def google_callback(request: Request, db: Session) -> RedirectResponse:
    try:
        token: dict[str, Any] = await oauth.google.authorize_access_token(request)
        userinfo = token.get("userinfo")
        if not userinfo:
            raise HTTPException(status_code=400, detail="Missing user info from Google")
        user = get_or_create_user(
            db,
            email=userinfo["email"],
            name=userinfo.get("name", userinfo["email"]),
            provider_sub=userinfo["sub"],
        )
        request.session["user_id"] = user.id
        return RedirectResponse(url=settings.frontend_url or "/")
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("Google OAuth callback failed")
        raise HTTPException(status_code=500, detail="Sign-in failed. Please try again.") from exc


def logout(request: Request) -> dict[str, str]:
    request.session.clear()
    return {"status": "logged_out"}
