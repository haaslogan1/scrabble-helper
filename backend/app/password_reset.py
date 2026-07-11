"""Forgot-password flow: email code then set a new password."""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.email_send import send_password_reset_email
from app.email_validation import validate_email
from app.models import PasswordReset, User
from app.passwords import hash_password, validate_password_policy

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 5
RESEND_COOLDOWN_SEC = 60
GENERIC_REQUEST_MESSAGE = (
    "If an account with that email can reset its password, we sent a 6-digit code. "
    "Check your inbox."
)


def _hash_code(email: str, code: str) -> str:
    payload = f"{email}:{code}".encode()
    key = settings.session_secret.encode()
    return hmac.new(key, payload, hashlib.sha256).hexdigest()


def _generate_code() -> str:
    return f"{secrets.randbelow(900_000) + 100_000:06d}"


def _generic_response(*, include_dev_code: str | None = None) -> dict[str, str | int | bool]:
    response: dict[str, str | int | bool] = {
        "message": GENERIC_REQUEST_MESSAGE,
        "expires_in_minutes": settings.email_verification_ttl_minutes,
    }
    if include_dev_code and settings.email_verification_dev_expose_code:
        response["dev_code"] = include_dev_code
    return response


def request_password_reset(db: Session, *, email: str) -> dict[str, str | int | bool]:
    try:
        email = validate_email(email)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    user = db.query(User).filter(User.email == email).one_or_none()
    if user is None or not user.password_hash:
        return _generic_response()

    now = datetime.utcnow()
    pending = db.query(PasswordReset).filter(PasswordReset.email == email).one_or_none()
    if pending is not None and pending.last_sent_at is not None:
        elapsed = (now - pending.last_sent_at).total_seconds()
        if elapsed < RESEND_COOLDOWN_SEC:
            return _generic_response()

    code = _generate_code()
    expires_at = now + timedelta(minutes=settings.email_verification_ttl_minutes)
    if pending is None:
        pending = PasswordReset(email=email)
        db.add(pending)
    pending.code_hash = _hash_code(email, code)
    pending.expires_at = expires_at
    pending.attempts = 0
    pending.last_sent_at = now
    if pending.created_at is None:
        pending.created_at = now
    db.commit()

    try:
        send_password_reset_email(to_email=email, code=code)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to send password reset email to %s", email)
        db.delete(pending)
        db.commit()
        raise HTTPException(
            status_code=503,
            detail="Could not send reset email. Try again later.",
        ) from exc

    return _generic_response(include_dev_code=code)


def confirm_password_reset(
    db: Session, *, email: str, code: str, new_password: str
) -> None:
    try:
        email = validate_email(email)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    code = code.strip()
    if not code.isdigit() or len(code) != 6:
        raise HTTPException(
            status_code=400,
            detail="Enter the 6-digit reset code from your email.",
        )

    try:
        validate_password_policy(new_password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    user = db.query(User).filter(User.email == email).one_or_none()
    if user is not None and not user.password_hash:
        raise HTTPException(
            status_code=400,
            detail="This account signs in with Google. Use Google sign-in instead of a password.",
        )

    pending = db.query(PasswordReset).filter(PasswordReset.email == email).one_or_none()
    if pending is None:
        raise HTTPException(
            status_code=400,
            detail="No password reset was requested for this email. Request a new code.",
        )

    if pending.expires_at < datetime.utcnow():
        db.delete(pending)
        db.commit()
        raise HTTPException(
            status_code=400,
            detail="Reset code expired. Request a new code and try again.",
        )

    if pending.attempts >= MAX_ATTEMPTS:
        db.delete(pending)
        db.commit()
        raise HTTPException(
            status_code=400,
            detail="Too many incorrect attempts. Request a new reset code.",
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
                detail="Too many incorrect attempts. Request a new reset code.",
            )
        raise HTTPException(
            status_code=400,
            detail=f"Incorrect reset code. {remaining} attempt(s) remaining.",
        )

    if user is None or not user.password_hash:
        db.delete(pending)
        db.commit()
        raise HTTPException(
            status_code=400,
            detail="No password reset was requested for this email. Request a new code.",
        )

    user.password_hash = hash_password(new_password)
    user.session_version = (user.session_version or 0) + 1
    db.delete(pending)
    db.commit()
