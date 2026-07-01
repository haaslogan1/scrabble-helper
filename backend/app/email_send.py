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
