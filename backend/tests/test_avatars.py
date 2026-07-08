from __future__ import annotations

import io

import pytest
from PIL import Image

from app import auth
from app.database import SessionLocal
from app.models import User
from tests.qa_gameplay import fresh_basic_client


def _png_bytes() -> bytes:
    image = Image.new("RGB", (200, 100), color=(30, 90, 180))
    out = io.BytesIO()
    image.save(out, format="PNG")
    return out.getvalue()


@pytest.fixture
def mock_storage(monkeypatch):
    store: dict[str, bytes] = {}

    def put_object(key: str, body: bytes, content_type: str) -> None:
        store[key] = body

    def delete_object(key: str) -> None:
        store.pop(key, None)

    def signed_url(key: str, *, expires_sec: int = 3600) -> str:
        return f"https://test.example/{key}"

    monkeypatch.setattr("app.storage.storage_configured", lambda: True)
    monkeypatch.setattr("app.storage.put_object", put_object)
    monkeypatch.setattr("app.storage.delete_object", delete_object)
    monkeypatch.setattr("app.storage.signed_url", signed_url)
    return store


@pytest.mark.integration
def test_upload_and_delete_avatar(mock_storage, monkeypatch):
    client, user = fresh_basic_client(monkeypatch, username="avataruser")
    assert user.get("avatar_url") is None

    res = client.post(
        "/api/me/avatar",
        files={"file": ("me.png", _png_bytes(), "image/png")},
    )
    assert res.status_code == 200, res.text
    payload = res.json()
    assert payload["has_custom_avatar"] is True
    assert payload["avatar_url"].startswith("https://test.example/users/")

    me = client.get("/auth/me")
    assert me.json()["has_custom_avatar"] is True

    deleted = client.delete("/api/me/avatar")
    assert deleted.status_code == 200
    assert deleted.json()["has_custom_avatar"] is False
    assert deleted.json()["avatar_url"] is None


@pytest.mark.integration
def test_google_picture_persisted_and_override(mock_storage, monkeypatch, db):
    with SessionLocal() as session:
        user = auth.get_or_create_user(
            session,
            email="google@test.local",
            name="Google User",
            provider_sub="google-sub-1",
            picture="https://googleusercontent.com/photo.jpg",
        )
        assert user.google_avatar_url == "https://googleusercontent.com/photo.jpg"
        assert user.avatar_storage_key is None
        user.avatar_storage_key = "users/99/avatar.jpg"
        session.commit()
        user_id = user.id

    with SessionLocal() as session:
        refreshed = session.get(User, user_id)
        assert refreshed is not None
        from app.storage import resolve_avatar_url

        assert resolve_avatar_url(refreshed).startswith("https://test.example/")


@pytest.mark.integration
def test_avatar_requires_auth(basic_client, mock_storage):
    res = basic_client.post(
        "/api/me/avatar",
        files={"file": ("me.png", _png_bytes(), "image/png")},
    )
    assert res.status_code == 401
