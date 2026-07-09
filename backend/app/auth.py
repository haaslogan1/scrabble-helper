from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Literal

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

DeviceLabel = Literal["mobile", "tablet", "computer"]

oauth = OAuth()
oauth.register(
    name="google",
    client_id=settings.google_client_id,
    client_secret=settings.google_client_secret,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


def get_or_create_user(
    db: Session, *, email: str, name: str, provider_sub: str, picture: str | None = None
) -> User:
    user = (
        db.query(User)
        .filter(User.provider == "google", User.provider_sub == provider_sub)
        .one_or_none()
    )
    if user:
        changed = False
        if user.email != email:
            user.email = email
            changed = True
        if user.name != name:
            user.name = name
            changed = True
        if picture and user.google_avatar_url != picture:
            user.google_avatar_url = picture
            changed = True
        if changed:
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
        if picture:
            existing.google_avatar_url = picture
        db.commit()
        db.refresh(existing)
        if not existing.username:
            assign_default_username(db, existing)
        return existing

    user = User(
        email=email,
        name=name,
        provider="google",
        provider_sub=provider_sub,
        google_avatar_url=picture,
    )
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


@dataclass
class SessionEstablished:
    user: User
    session_replaced: bool
    replaced_device_label: DeviceLabel | None


def parse_device_label(user_agent: str | None) -> DeviceLabel | None:
    if not user_agent:
        return None
    ua = user_agent.lower()
    if "ipad" in ua or "tablet" in ua:
        return "tablet"
    if any(token in ua for token in ("iphone", "android", "mobile")):
        return "mobile"
    return "computer"


def session_superseded_error() -> HTTPException:
    return HTTPException(
        status_code=401,
        detail={
            "code": "session_superseded",
            "message": "Your session was ended because you signed in elsewhere.",
        },
    )


def validate_session_version(request: Request, user: User) -> None:
    cookie_version = request.session.get("session_version")
    if cookie_version is None:
        if user.session_version != 0:
            raise session_superseded_error()
        return
    if cookie_version != user.session_version:
        raise session_superseded_error()


def validate_ws_session_version(session: dict, user: User) -> None:
    cookie_version = session.get("session_version")
    if cookie_version is None:
        if user.session_version != 0:
            raise session_superseded_error()
        return
    if cookie_version != user.session_version:
        raise session_superseded_error()


def establish_session(
    db: Session,
    request: Request,
    user: User,
    *,
    user_agent: str | None = None,
) -> SessionEstablished:
    session_replaced = user.session_version >= 1
    replaced_device_label = (
        parse_device_label(user.last_session_user_agent) if session_replaced else None
    )

    user.session_version += 1
    if user_agent:
        user.last_session_user_agent = user_agent[:512]
    db.commit()
    db.refresh(user)

    request.session["user_id"] = user.id
    request.session["session_version"] = user.session_version

    return SessionEstablished(
        user=user,
        session_replaced=session_replaced,
        replaced_device_label=replaced_device_label,
    )


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
    validate_session_version(request, user)
    return user


def require_admin(request: Request, db: Session) -> User:
    user = get_current_user(request, db)
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


def register_basic_user(
    db: Session, request: Request, *, email: str, password: str, name: str
) -> SessionEstablished:
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
    user_agent = request.headers.get("user-agent")
    return establish_session(db, request, user, user_agent=user_agent)


def login_basic_user(db: Session, request: Request, *, email: str, password: str) -> SessionEstablished:
    try:
        email = validate_email(email)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    user = db.query(User).filter(User.email == email).one_or_none()
    if user is None or not user.password_hash:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    user_agent = request.headers.get("user-agent")
    return establish_session(db, request, user, user_agent=user_agent)


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
    request.session.pop("session_version", None)
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
            picture=userinfo.get("picture"),
        )
        user_agent = request.headers.get("user-agent")
        established = establish_session(db, request, user, user_agent=user_agent)
        redirect_url = settings.frontend_url or "/"
        if established.session_replaced:
            params = "session_replaced=1"
            if established.replaced_device_label:
                params += f"&device={established.replaced_device_label}"
            separator = "&" if "?" in redirect_url else "?"
            redirect_url = f"{redirect_url}{separator}{params}"
        return RedirectResponse(url=redirect_url)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("Google OAuth callback failed")
        raise HTTPException(status_code=500, detail="Sign-in failed. Please try again.") from exc


def logout(request: Request) -> dict[str, str]:
    request.session.clear()
    return {"status": "logged_out"}
