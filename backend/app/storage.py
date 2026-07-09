from __future__ import annotations

import io
import logging
from typing import TYPE_CHECKING

from botocore.exceptions import BotoCoreError, ClientError
from fastapi import HTTPException
from PIL import Image, ImageOps, UnidentifiedImageError

from app.config import settings

if TYPE_CHECKING:
    from app.models import User

logger = logging.getLogger(__name__)

_ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
_JPEG_CONTENT_TYPE = "image/jpeg"


def storage_configured() -> bool:
    return bool(
        settings.s3_endpoint
        and settings.s3_bucket
        and settings.s3_access_key
        and settings.s3_secret_key
    )


def _s3_client():
    import boto3

    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region or "auto",
    )


def _require_storage() -> None:
    if not storage_configured():
        raise HTTPException(status_code=503, detail="Photo storage is not configured")


def _open_image(file_bytes: bytes) -> Image.Image:
    if len(file_bytes) > settings.photo_max_bytes:
        raise HTTPException(status_code=400, detail="Image file is too large")
    try:
        image = Image.open(io.BytesIO(file_bytes))
        image.load()
    except UnidentifiedImageError as exc:
        raise HTTPException(status_code=400, detail="Invalid image file") from exc
    if image.format not in _ALLOWED_FORMATS:
        raise HTTPException(status_code=400, detail="Unsupported image format")
    return ImageOps.exif_transpose(image)


def _to_jpeg_bytes(image: Image.Image, *, max_dimension: int) -> bytes:
    if image.mode not in ("RGB", "L"):
        image = image.convert("RGB")
    image.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
    out = io.BytesIO()
    image.save(out, format="JPEG", quality=85, optimize=True)
    return out.getvalue()


def process_image(file_bytes: bytes) -> tuple[bytes, str]:
    if len(file_bytes) > settings.photo_max_bytes:
        raise HTTPException(status_code=400, detail="Image file is too large")
    image = _open_image(file_bytes)
    body = _to_jpeg_bytes(image, max_dimension=settings.photo_max_dimension)
    return body, _JPEG_CONTENT_TYPE


def process_avatar(file_bytes: bytes) -> tuple[bytes, str]:
    if len(file_bytes) > settings.avatar_max_bytes:
        raise HTTPException(status_code=400, detail="Image file is too large")
    image = _open_image(file_bytes)
    width, height = image.size
    side = min(width, height)
    left = (width - side) // 2
    top = (height - side) // 2
    image = image.crop((left, top, left + side, top + side))
    body = _to_jpeg_bytes(image, max_dimension=settings.avatar_max_dimension)
    return body, _JPEG_CONTENT_TYPE


def put_object(key: str, body: bytes, content_type: str) -> None:
    _require_storage()
    try:
        _s3_client().put_object(
            Bucket=settings.s3_bucket,
            Key=key,
            Body=body,
            ContentType=content_type,
        )
    except (BotoCoreError, ClientError) as exc:
        logger.exception("S3 put_object failed for key %s", key)
        raise HTTPException(status_code=502, detail="Failed to store image") from exc


def delete_object(key: str) -> None:
    if not storage_configured():
        return
    try:
        _s3_client().delete_object(Bucket=settings.s3_bucket, Key=key)
    except (BotoCoreError, ClientError) as exc:
        logger.exception("S3 delete_object failed for key %s", key)
        raise HTTPException(status_code=502, detail="Failed to delete image") from exc


def signed_url(key: str, *, expires_sec: int = 3600) -> str:
    _require_storage()
    try:
        return _s3_client().generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.s3_bucket, "Key": key},
            ExpiresIn=expires_sec,
        )
    except (BotoCoreError, ClientError) as exc:
        logger.exception("S3 signed_url failed for key %s", key)
        raise HTTPException(status_code=502, detail="Failed to generate image URL") from exc


def resolve_avatar_url(user: User) -> str | None:
    if user.avatar_storage_key:
        if not storage_configured():
            return None
        try:
            return signed_url(user.avatar_storage_key)
        except HTTPException:
            return None
    return user.google_avatar_url
