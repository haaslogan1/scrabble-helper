from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from app.config import settings

logger = logging.getLogger(__name__)


def smtp_configured() -> bool:
    return bool(settings.smtp_host and settings.smtp_from)


def send_verification_email(*, to_email: str, code: str) -> None:
    subject = "Your Scrabble Helper verification code"
    body = (
        f"Your verification code is: {code}\n\n"
        f"This code expires in {settings.email_verification_ttl_minutes} minutes.\n"
        "If you did not request this, you can ignore this email."
    )
    if not smtp_configured():
        if settings.email_verification_dev_expose_code:
            logger.info("SMTP not configured; verification code for %s: %s", to_email, code)
            return
        raise RuntimeError(
            "Email sending is not configured. Set SMTP_HOST and SMTP_FROM on the server."
        )

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.smtp_from
    message["To"] = to_email
    message.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
        if settings.smtp_use_tls:
            smtp.starttls()
        if settings.smtp_user:
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(message)


def send_feedback_email(
    *,
    to_email: str,
    from_user_email: str,
    from_user_name: str,
    message: str,
    category: str | None,
    page_url: str | None,
    game_id: int | None,
) -> None:
    label = category or "General"
    subject = f"[Scrabble Helper Feedback] {label} from {from_user_email}"
    lines = [
        f"From: {from_user_name} ({from_user_email})",
        f"Category: {label}",
    ]
    if page_url:
        lines.append(f"Page: {page_url}")
    if game_id is not None:
        lines.append(f"Game ID: {game_id}")
    lines.extend(["", message])
    body = "\n".join(lines)

    if not smtp_configured():
        if settings.email_verification_dev_expose_code:
            logger.info(
                "SMTP not configured; feedback from %s (%s): %s",
                from_user_email,
                label,
                message[:200],
            )
            return
        raise RuntimeError(
            "Email sending is not configured. Set SMTP_HOST and SMTP_FROM on the server."
        )

    email = EmailMessage()
    email["Subject"] = subject
    email["From"] = settings.smtp_from
    email["To"] = to_email
    email.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
        if settings.smtp_use_tls:
            smtp.starttls()
        if settings.smtp_user:
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(email)


def send_password_reset_email(*, to_email: str, code: str) -> None:
    subject = "Your Scrabble Helper password reset code"
    body = (
        f"Your password reset code is: {code}\n\n"
        f"This code expires in {settings.email_verification_ttl_minutes} minutes.\n"
        "If you did not request a password reset, you can ignore this email."
    )
    if not smtp_configured():
        if settings.email_verification_dev_expose_code:
            logger.info("SMTP not configured; password reset code for %s: %s", to_email, code)
            return
        raise RuntimeError(
            "Email sending is not configured. Set SMTP_HOST and SMTP_FROM on the server."
        )

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.smtp_from
    message["To"] = to_email
    message.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
        if settings.smtp_use_tls:
            smtp.starttls()
        if settings.smtp_user:
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(message)
