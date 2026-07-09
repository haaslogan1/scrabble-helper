"""Shared helpers for gameplay QA tests and the QA agent."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

DEFAULT_PASSWORD = "QaTestPass1"


def _auth_user(data: dict) -> dict:
    return data["user"]


def register_basic_user(
    client: TestClient,
    *,
    email: str,
    password: str = DEFAULT_PASSWORD,
    name: str = "QA User",
) -> dict:
    send = client.post(
        "/auth/register/send-code",
        json={"email": email, "password": password, "name": name},
    )
    assert send.status_code == 200, send.text
    payload = send.json()
    code = payload.get("dev_code")
    assert code, "dev_code missing; set EMAIL_VERIFICATION_DEV_EXPOSE_CODE=true in tests"
    res = client.post(
        "/auth/register/verify",
        json={"email": email, "code": code},
    )
    assert res.status_code == 200, res.text
    return _auth_user(res.json())


def register_user_with_username(
    client: TestClient,
    *,
    email: str,
    username: str,
    name: str | None = None,
    password: str = DEFAULT_PASSWORD,
) -> dict:
    user = register_basic_user(
        client, email=email, password=password, name=name or username.title()
    )
    res = client.patch("/api/me", json={"username": username})
    assert res.status_code == 200, res.text
    return res.json()


def login_basic_user(
    client: TestClient, *, email: str, password: str = DEFAULT_PASSWORD
) -> dict:
    res = client.post("/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text
    return _auth_user(res.json())


def make_basic_client(monkeypatch) -> TestClient:
    from app.config import settings
    from app.main import app

    monkeypatch.setattr(settings, "dev_auth_bypass", False)
    monkeypatch.setattr(settings, "local_auth_enabled", True)
    monkeypatch.setattr(settings, "email_verification_enabled", True)
    monkeypatch.setattr(settings, "email_verification_dev_expose_code", True)
    return TestClient(app)


def fresh_basic_client(monkeypatch, *, email: str | None = None, username: str | None = None, name: str | None = None):
    client = make_basic_client(monkeypatch)
    email = email or f"user-{uuid.uuid4().hex[:8]}@test.local"
    display_name = name or (username.title() if username else "QA User")
    if username:
        return client, register_user_with_username(
            client, email=email, username=username, name=display_name
        )
    return client, register_basic_user(client, email=email, name=display_name)


def add_friend(client: TestClient, *, user_id: int | None = None, username: str | None = None) -> dict:
    body: dict = {}
    if user_id is not None:
        body["user_id"] = user_id
    if username is not None:
        body["username"] = username
    res = client.post("/api/friends", json=body)
    assert res.status_code == 200, res.text
    return _auth_user(res.json())


def accept_friend_request(client: TestClient, request_id: int) -> dict:
    res = client.post(f"/api/friends/requests/{request_id}/accept")
    assert res.status_code == 200, res.text
    return _auth_user(res.json())


def add_mutual_friends(
    from_client: TestClient,
    to_client: TestClient,
    *,
    to_user_id: int,
) -> None:
    result = add_friend(from_client, user_id=to_user_id)
    if result.get("mutual"):
        return
    incoming = to_client.get("/api/friends/requests/incoming")
    assert incoming.status_code == 200, incoming.text
    requests = incoming.json()
    assert requests, "expected incoming friend request"
    accept_friend_request(to_client, requests[0]["id"])


def begin_game_with_player_ids(client: TestClient, game_id: int, player_ids: list[int]) -> dict:
    abandon_in_progress_games(client)
    attach = client.put(f"/api/games/{game_id}/players", json={"player_ids": player_ids})
    assert attach.status_code == 200, attach.text
    begin = client.post(f"/api/games/{game_id}/begin")
    assert begin.status_code == 200, begin.text
    return begin.json()


def connect_game_watch_ws(client: TestClient, game_id: int):
    return client.websocket_connect(f"/api/games/{game_id}/watch")


def create_roster(client: TestClient, names: list[str]) -> list[int]:
    ids = []
    for name in names:
        res = client.post("/api/players", json={"name": name})
        assert res.status_code == 200, res.text
        ids.append(res.json()["id"])
    return ids


def setup_and_begin_game(
    client: TestClient,
    player_names: list[str],
    *,
    settings: dict | None = None,
) -> int:
    abandon_in_progress_games(client)
    ids = create_roster(client, player_names)
    body: dict = {}
    if settings:
        body["settings"] = settings
    game_res = client.post("/api/games", json=body)
    assert game_res.status_code == 200, game_res.text
    game_id = game_res.json()["id"]
    attach = client.put(f"/api/games/{game_id}/players", json={"player_ids": ids})
    assert attach.status_code == 200, attach.text
    begin = client.post(f"/api/games/{game_id}/begin")
    assert begin.status_code == 200, begin.text
    return game_id


def play_turn(client: TestClient, game_id: int, points: int) -> dict:
    res = client.post(
        f"/api/games/{game_id}/turns",
        json={"points": points, "play_type": "score"},
    )
    return res


def abandon_in_progress_games(client: TestClient) -> None:
    """Finish active games so the owner's linked player can join a new live game."""
    for status in ("active", "ending"):
        listing = client.get("/api/games", params={"status": status})
        if listing.status_code != 200:
            continue
        for summary in listing.json():
            gid = summary["id"]
            state = client.get(f"/api/games/{gid}/state").json()
            client.post(f"/api/games/{gid}/end")
            racks = {str(s["player_id"]): 0 for s in state["standings"]}
            client.post(
                f"/api/games/{gid}/finalize",
                json={"rack_adjustments": racks},
            )


def roster_player_ids(state_or_attach: dict) -> list[int]:
    return [s["player_id"] for s in state_or_attach["standings"]]


def attach_opponents(client: TestClient, game_id: int, opponent_ids: list[int]) -> dict:
    """Attach opponents; the game owner is auto-included by the backend."""
    res = client.put(f"/api/games/{game_id}/players", json={"player_ids": opponent_ids})
    assert res.status_code == 200, res.text
    return _auth_user(res.json())


def play_full_game(
    client: TestClient,
    game_id: int,
    player_count: int | None = None,
    rounds: int = 1,
    score_fn=None,
) -> None:
    if player_count is None:
        state = client.get(f"/api/games/{game_id}/state").json()
        player_count = len(state["standings"])
    if score_fn is None:
        score_fn = lambda r, p: 10 + r + p
    for round_num in range(1, rounds + 1):
        for player_idx in range(player_count):
            points = score_fn(round_num, player_idx)
            res = play_turn(client, game_id, points)
            assert res.status_code == 200, res.text


def finalize_game(client: TestClient, game_id: int, player_ids: list[int]) -> dict:
    end = client.post(f"/api/games/{game_id}/end")
    assert end.status_code == 200, end.text
    racks = {str(pid): 0 for pid in player_ids}
    fin = client.post(
        f"/api/games/{game_id}/finalize",
        json={"rack_adjustments": racks},
    )
    assert fin.status_code == 200, fin.text
    return fin.json()
