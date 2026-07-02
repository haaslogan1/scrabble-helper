from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Notification, NotificationType


def create_notification(
    db: Session,
    user_id: int,
    ntype: NotificationType,
    *,
    title: str,
    body: str,
    payload: dict[str, Any] | None = None,
) -> Notification:
    notification = Notification(
        user_id=user_id,
        type=ntype,
        title=title,
        body=body,
        payload=payload or {},
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def notification_out(n: Notification) -> dict[str, Any]:
    return {
        "id": n.id,
        "type": n.type.value,
        "title": n.title,
        "body": n.body,
        "payload": n.payload,
        "read": n.read_at is not None,
        "created_at": n.created_at.isoformat(),
    }


def list_notifications(db: Session, user_id: int, *, limit: int = 50) -> list[dict[str, Any]]:
    rows = (
        db.query(Notification)
        .filter(Notification.user_id == user_id, Notification.dismissed_at.is_(None))
        .order_by(Notification.created_at.desc())
        .limit(limit)
        .all()
    )
    return [notification_out(n) for n in rows]


def unread_count(db: Session, user_id: int) -> int:
    return (
        db.query(Notification)
        .filter(
            Notification.user_id == user_id,
            Notification.read_at.is_(None),
            Notification.dismissed_at.is_(None),
        )
        .count()
    )


def get_notification(db: Session, user_id: int, notification_id: int) -> Notification:
    notification = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == user_id)
        .one_or_none()
    )
    if notification is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notification


def mark_read(db: Session, user_id: int, notification_id: int) -> dict[str, Any]:
    notification = get_notification(db, user_id, notification_id)
    if notification.read_at is None:
        notification.read_at = datetime.utcnow()
        db.commit()
        db.refresh(notification)
    return notification_out(notification)


def dismiss(db: Session, user_id: int, notification_id: int) -> dict[str, str]:
    notification = get_notification(db, user_id, notification_id)
    if notification.dismissed_at is None:
        notification.dismissed_at = datetime.utcnow()
        if notification.read_at is None:
            notification.read_at = notification.dismissed_at
        db.commit()
    return {"status": "ok"}


def mark_all_read(db: Session, user_id: int) -> dict[str, str]:
    now = datetime.utcnow()
    (
        db.query(Notification)
        .filter(
            Notification.user_id == user_id,
            Notification.read_at.is_(None),
            Notification.dismissed_at.is_(None),
        )
        .update({Notification.read_at: now}, synchronize_session=False)
    )
    db.commit()
    return {"status": "ok"}


def dismiss_for_friend_request(db: Session, user_id: int, friend_request_id: int) -> None:
    for notification in (
        db.query(Notification)
        .filter(
            Notification.user_id == user_id,
            Notification.type == NotificationType.friend_request,
            Notification.dismissed_at.is_(None),
        )
        .all()
    ):
        if notification.payload.get("friend_request_id") == friend_request_id:
            now = datetime.utcnow()
            notification.dismissed_at = now
            if notification.read_at is None:
                notification.read_at = now
    db.commit()
