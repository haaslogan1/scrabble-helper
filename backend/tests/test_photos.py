from __future__ import annotations

import io

import pytest
from PIL import Image

from tests.qa_gameplay import (
    add_mutual_friends,
    begin_game_with_player_ids,
    fresh_basic_client,
    setup_and_begin_game,
)


def _friend_player_id(host_client, friend_user_id: int) -> int:
    players = host_client.get("/api/players").json()
    return next(p["id"] for p in players if p.get("linked_user_id") == friend_user_id)


def _png_bytes() -> bytes:
    image = Image.new("RGB", (120, 80), color=(20, 120, 60))
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

    def configured() -> bool:
        return True

    monkeypatch.setattr("app.storage.storage_configured", configured)
    monkeypatch.setattr("app.storage.put_object", put_object)
    monkeypatch.setattr("app.storage.delete_object", delete_object)
    monkeypatch.setattr("app.storage.signed_url", signed_url)
    return store


@pytest.mark.integration
def test_upload_game_photo_as_owner(mock_storage, monkeypatch):
    client_a, user_a = fresh_basic_client(monkeypatch, username="photoowner")
    client_b, user_b = fresh_basic_client(monkeypatch, username="photospec")

    add_mutual_friends(client_a, client_b, to_user_id=user_b["id"])

    bob_player_id = _friend_player_id(client_a, user_b["id"])
    manual = client_a.post("/api/players", json={"name": "Manual Host"}).json()["id"]
    game_id = client_a.post("/api/games", json={}).json()["id"]
    begin_game_with_player_ids(client_a, game_id, [manual, bob_player_id])

    res = client_a.post(
        f"/api/games/{game_id}/photos",
        files={"file": ("board.png", _png_bytes(), "image/png")},
        data={"caption": "Opening board", "context": "board"},
    )
    assert res.status_code == 201, res.text
    payload = res.json()
    assert payload["caption"] == "Opening board"
    assert payload["context"] == "board"
    assert payload["url"].startswith("https://test.example/games/")

    listed = client_a.get(f"/api/games/{game_id}/photos")
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    spectator_list = client_b.get(f"/api/games/{game_id}/photos")
    assert spectator_list.status_code == 200
    assert len(spectator_list.json()) == 1

    upload_as_spectator = client_b.post(
        f"/api/games/{game_id}/photos",
        files={"file": ("board.png", _png_bytes(), "image/png")},
    )
    assert upload_as_spectator.status_code == 403

    photo_id = payload["id"]
    denied_delete = client_b.delete(f"/api/games/{game_id}/photos/{photo_id}")
    assert denied_delete.status_code == 403

    deleted = client_a.delete(f"/api/games/{game_id}/photos/{photo_id}")
    assert deleted.status_code == 204
    assert client_a.get(f"/api/games/{game_id}/photos").json() == []


@pytest.mark.integration
def test_game_photo_requires_storage(monkeypatch):
    client, _user = fresh_basic_client(monkeypatch, username="nostorage")
    monkeypatch.setattr("app.storage.storage_configured", lambda: False)
    game_id = setup_and_begin_game(client, ["Me", "You"])
    res = client.post(
        f"/api/games/{game_id}/photos",
        files={"file": ("board.png", _png_bytes(), "image/png")},
    )
    assert res.status_code == 503
