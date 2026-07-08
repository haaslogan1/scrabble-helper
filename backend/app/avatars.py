from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.models import User
from app import storage
from app.schemas import FriendOut, UserOut, UserSearchOut

_avatar_upload_times: dict[int, list[datetime]] = {}


def _check_avatar_rate_limit(user_id: int) -> None:
    now = datetime.utcnow()
    cutoff = now - timedelta(hours=1)
    times = [t for t in _avatar_upload_times.get(user_id, []) if t > cutoff]
    if len(times) >= settings.avatar_upload_rate_limit_per_hour:
        raise HTTPException(
            status_code=429,
            detail="Too many avatar uploads. Please try again later.",
        )
    times.append(now)
    _avatar_upload_times[user_id] = times


def user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        name=user.name,
        username=user.username,
        is_admin=user.is_admin,
        avatar_url=storage.resolve_avatar_url(user),
        has_custom_avatar=bool(user.avatar_storage_key),
        provider=user.provider,
    )


def friend_out(friend: User, *, mutual: bool) -> FriendOut:
    return FriendOut(
        id=friend.id,
        username=friend.username,
        name=friend.name,
        mutual=mutual,
        avatar_url=storage.resolve_avatar_url(friend),
    )


def user_search_out(user: User, *, reason: str | None = None) -> UserSearchOut:
    return UserSearchOut(
        id=user.id,
        username=user.username,
        name=user.name,
        reason=reason,
        avatar_url=storage.resolve_avatar_url(user),
    )


async def upload_avatar(db: Session, user: User, file: UploadFile) -> UserOut:
    if not storage.storage_configured():
        raise HTTPException(status_code=503, detail="Photo storage is not configured")
    _check_avatar_rate_limit(user.id)

    raw = await file.read()
    body, content_type = storage.process_avatar(raw)
    key = f"users/{user.id}/avatar.jpg"

    if user.avatar_storage_key and user.avatar_storage_key != key:
        storage.delete_object(user.avatar_storage_key)

    storage.put_object(key, body, content_type)
    user.avatar_storage_key = key
    db.commit()
    db.refresh(user)
    return user_out(user)


def delete_avatar(db: Session, user: User) -> UserOut:
    if user.avatar_storage_key:
        storage.delete_object(user.avatar_storage_key)
        user.avatar_storage_key = None
        db.commit()
        db.refresh(user)
    return user_out(user)
