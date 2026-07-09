from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
from datetime import datetime, timedelta

from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from app.auth import SessionEstablished, establish_session
from app.config import settings
from app.email_send import send_verification_email
from app.email_validation import validate_email
from app.friends import assign_default_username
from app.models import EmailVerification, User
from app.passwords import hash_password, validate_password_policy

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 5


def _hash_code(email: str, code: str) -> str:
    payload = f"{email}:{code}".encode()
    key = settings.session_secret.encode()
    return hmac.new(key, payload, hashlib.sha256).hexdigest()


def _generate_code() -> str:
    return f"{secrets.randbelow(900_000) + 100_000:06d}"


def request_registration_code(
    db: Session, *, email: str, password: str, name: str
) -> dict[str, str | int | bool]:
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

    code = _generate_code()
    expires_at = datetime.utcnow() + timedelta(minutes=settings.email_verification_ttl_minutes)
    pending = db.query(EmailVerification).filter(EmailVerification.email == email).one_or_none()
    if pending is None:
        pending = EmailVerification(email=email)
        db.add(pending)
    pending.code_hash = _hash_code(email, code)
    pending.name = name.strip() or email.split("@")[0]
    pending.password_hash = hash_password(password)
    pending.expires_at = expires_at
    pending.attempts = 0
    db.commit()

    try:
        send_verification_email(to_email=email, code=code)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to send verification email to %s", email)
        db.delete(pending)
        db.commit()
        raise HTTPException(
            status_code=503,
            detail="Could not send verification email. Check the address and try again later.",
        ) from exc

    response: dict[str, str | int | bool] = {
        "message": f"We sent a 6-digit code to {email}. Enter it below to finish creating your account.",
        "expires_in_minutes": settings.email_verification_ttl_minutes,
    }
    if settings.email_verification_dev_expose_code:
        response["dev_code"] = code
    return response


def complete_registration(
    db: Session, request: Request, *, email: str, code: str
) -> SessionEstablished:
    try:
        email = validate_email(email)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    code = code.strip()
    if not code.isdigit() or len(code) != 6:
        raise HTTPException(
            status_code=400,
            detail="Enter the 6-digit verification code from your email.",
        )

    pending = db.query(EmailVerification).filter(EmailVerification.email == email).one_or_none()
    if pending is None:
        raise HTTPException(
            status_code=400,
            detail="No verification code was requested for this email. Start account creation again.",
        )

    if pending.expires_at < datetime.utcnow():
        db.delete(pending)
        db.commit()
        raise HTTPException(
            status_code=400,
            detail="Verification code expired. Request a new code and try again.",
        )

    if pending.attempts >= MAX_ATTEMPTS:
        db.delete(pending)
        db.commit()
        raise HTTPException(
            status_code=400,
            detail="Too many incorrect attempts. Request a new verification code.",
        )

    if not hmac.compare_digest(pending.code_hash, _hash_code(email, code)):
        pending.attempts += 1
        db.commit()
        remaining = MAX_ATTEMPTS - pending.attempts
        if remaining <= 0:
            db.delete(pending)
            db.commit()
            raise HTTPException(
                status_code=400,
                detail="Too many incorrect attempts. Request a new verification code.",
            )
        raise HTTPException(
            status_code=400,
            detail=f"Incorrect verification code. {remaining} attempt(s) remaining.",
        )

    existing = db.query(User).filter(User.email == email).one_or_none()
    if existing:
        db.delete(pending)
        db.commit()
        raise HTTPException(
            status_code=409,
            detail="An account with this email already exists. Try signing in instead.",
        )

    user = User(
        email=email,
        name=pending.name,
        provider="local",
        provider_sub=email,
        password_hash=pending.password_hash,
        is_admin=False,
    )
    db.add(user)
    db.delete(pending)
    db.commit()
    db.refresh(user)
    assign_default_username(db, user)
    user_agent = request.headers.get("user-agent")
    return establish_session(db, request, user, user_agent=user_agent)
