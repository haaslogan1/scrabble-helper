from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.models import GamePhoto, PhotoContext, User
from app import storage
from app.services import get_game_access, require_game_owner


def _photo_out(photo: GamePhoto) -> dict:
    return {
        "id": photo.id,
        "url": storage.signed_url(photo.storage_key),
        "caption": photo.caption,
        "context": photo.context.value,
        "created_at": photo.created_at,
        "uploaded_by_name": photo.uploaded_by.name,
    }


def _check_game_photo_rate_limit(db: Session, game_id: int) -> None:
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    recent_count = (
        db.query(GamePhoto)
        .filter(GamePhoto.game_id == game_id, GamePhoto.created_at > one_hour_ago)
        .count()
    )
    if recent_count >= settings.photo_upload_rate_limit_per_game:
        raise HTTPException(
            status_code=429,
            detail="Too many photo uploads for this game. Please try again later.",
        )


def _parse_context(value: str | None) -> PhotoContext:
    if not value:
        return PhotoContext.board
    try:
        return PhotoContext(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid photo context") from exc


async def upload_game_photo(
    db: Session,
    user: User,
    game_id: int,
    file: UploadFile,
    *,
    caption: str | None = None,
    context: str | None = None,
    round_id: int | None = None,
) -> dict:
    require_game_owner(db, user.id, game_id)
    if not storage.storage_configured():
        raise HTTPException(status_code=503, detail="Photo storage is not configured")
    _check_game_photo_rate_limit(db, game_id)

    raw = await file.read()
    body, content_type = storage.process_image(raw)
    key = f"games/{game_id}/{uuid.uuid4().hex}.jpg"
    storage.put_object(key, body, content_type)

    photo = GamePhoto(
        game_id=game_id,
        uploaded_by_user_id=user.id,
        storage_key=key,
        content_type=content_type,
        caption=(caption or "").strip()[:500] or None,
        context=_parse_context(context),
        round_id=round_id,
    )
    db.add(photo)
    db.commit()
    db.refresh(photo)
    photo.uploaded_by = user
    return _photo_out(photo)


def list_game_photos(db: Session, user_id: int, game_id: int) -> list[dict]:
    get_game_access(db, user_id, game_id)
    if not storage.storage_configured():
        return []
    photos = (
        db.query(GamePhoto)
        .options(joinedload(GamePhoto.uploaded_by))
        .filter(GamePhoto.game_id == game_id)
        .order_by(GamePhoto.created_at.desc())
        .all()
    )
    return [_photo_out(photo) for photo in photos]


def delete_game_photo(db: Session, user_id: int, game_id: int, photo_id: int) -> None:
    require_game_owner(db, user_id, game_id)
    photo = (
        db.query(GamePhoto)
        .filter(GamePhoto.id == photo_id, GamePhoto.game_id == game_id)
        .one_or_none()
    )
    if photo is None:
        raise HTTPException(status_code=404, detail="Photo not found")
    storage.delete_object(photo.storage_key)
    db.delete(photo)
    db.commit()
