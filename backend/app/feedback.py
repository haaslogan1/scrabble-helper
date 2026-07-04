from __future__ import annotations

import logging
from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.email_send import send_feedback_email
from app.models import FeedbackSubmission, User
from app.schemas import FeedbackCreate

logger = logging.getLogger(__name__)


def submit_feedback(db: Session, user: User, body: FeedbackCreate) -> None:
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    recent_count = (
        db.query(FeedbackSubmission)
        .filter(
            FeedbackSubmission.user_id == user.id,
            FeedbackSubmission.created_at > one_hour_ago,
        )
        .count()
    )
    if recent_count >= settings.feedback_rate_limit_per_hour:
        raise HTTPException(
            status_code=429,
            detail="Too many feedback submissions. Please try again later.",
        )

    row = FeedbackSubmission(
        user_id=user.id,
        category=body.category,
        message=body.message,
        page_url=body.page_url,
        game_id=body.game_id,
        reviewed=False,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    to_email = settings.feedback_to_email.strip()
    if not to_email:
        logger.warning("FEEDBACK_TO_EMAIL not configured; feedback id=%s stored only", row.id)
        return

    try:
        send_feedback_email(
            to_email=to_email,
            from_user_email=user.email,
            from_user_name=user.name,
            message=body.message,
            category=body.category,
            page_url=body.page_url,
            game_id=body.game_id,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to send feedback email for submission id=%s", row.id)
        db.delete(row)
        db.commit()
        raise HTTPException(
            status_code=503,
            detail="Could not send feedback. Please try again later.",
        ) from exc
