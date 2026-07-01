"""Shared helpers for gameplay QA tests and the QA agent."""

from __future__ import annotations

from fastapi.testclient import TestClient

DEFAULT_PASSWORD = "QaTestPass1"


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
    return res.json()


def login_basic_user(
    client: TestClient, *, email: str, password: str = DEFAULT_PASSWORD
) -> dict:
    res = client.post("/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text
    return res.json()


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


def play_full_game(
    client: TestClient,
    game_id: int,
    player_count: int,
    rounds: int,
    score_fn=None,
) -> None:
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
