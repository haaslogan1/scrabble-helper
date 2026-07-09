from __future__ import annotations

import io

from PIL import Image

from app.storage import _open_image, process_avatar, process_image

_ORIENTATION_TAG = 274


def _jpeg_with_exif_orientation(width: int, height: int, orientation: int) -> bytes:
    image = Image.new("RGB", (width, height), color=(255, 0, 0))
    exif = image.getexif()
    exif[_ORIENTATION_TAG] = orientation
    out = io.BytesIO()
    image.save(out, format="JPEG", exif=exif)
    return out.getvalue()


def _jpeg_dimensions(jpeg_bytes: bytes) -> tuple[int, int]:
    with Image.open(io.BytesIO(jpeg_bytes)) as image:
        return image.size


def test_open_image_applies_exif_orientation():
    raw = _jpeg_with_exif_orientation(200, 100, orientation=6)
    assert _open_image(raw).size == (100, 200)


def test_open_image_without_exif_unchanged():
    raw = _jpeg_with_exif_orientation(100, 200, orientation=1)
    assert _open_image(raw).size == (100, 200)


def test_process_avatar_with_exif_orientation():
    raw = _jpeg_with_exif_orientation(200, 100, orientation=6)
    body, _ = process_avatar(raw)
    width, height = _jpeg_dimensions(body)
    assert width == height == 100


def test_process_image_applies_exif_orientation_before_resize():
    raw = _jpeg_with_exif_orientation(200, 100, orientation=6)
    body, _ = process_image(raw)
    width, height = _jpeg_dimensions(body)
    assert height > width
