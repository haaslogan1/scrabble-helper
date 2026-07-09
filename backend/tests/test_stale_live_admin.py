import uuid
from datetime import datetime, timedelta

import pytest

from app.models import Game, GameStatus
from tests.qa_gameplay import (
    add_mutual_friends,
    begin_game_with_player_ids,
    fresh_basic_client,
    register_basic_user,
)


def _friend_player_id(host_client, friend_user_id: int) -> int:
    players = host_client.get("/api/players").json()
    return next(p["id"] for p in players if p.get("linked_user_id") == friend_user_id)


def _set_last_activity(db, game_id: int, hours_ago: float) -> None:
    game = db.get(Game, game_id)
    game.last_activity_at = datetime.utcnow() - timedelta(hours=hours_ago)
    db.commit()


@pytest.mark.integration
def test_admin_force_complete_stale_game(admin_client, basic_client, db):
    from tests.qa_gameplay import setup_and_begin_game

    register_basic_user(basic_client, email=f"victim-{uuid.uuid4().hex[:8]}@test.local")
    game_id = setup_and_begin_game(basic_client, ["adm1", "adm2"])
    _set_last_activity(db, game_id, 1)

    res = admin_client.post(f"/api/admin/games/{game_id}/force-complete")
    assert res.status_code == 200
    assert res.json()["status"] == "completed"
    assert db.get(Game, game_id).status == GameStatus.completed


@pytest.mark.integration
def test_admin_sweep_stale_games(admin_client, basic_client, db):
    from tests.qa_gameplay import setup_and_begin_game

    register_basic_user(basic_client, email=f"victim-{uuid.uuid4().hex[:8]}@test.local")
    game_id = setup_and_begin_game(basic_client, ["sw1", "sw2"])
    _set_last_activity(db, game_id, 4)

    res = admin_client.post("/api/admin/games/sweep-stale")
    assert res.status_code == 200
    assert res.json()["swept"] >= 1
    assert db.get(Game, game_id).status == GameStatus.completed


@pytest.mark.integration
def test_admin_list_games_by_participant_email(admin_client, monkeypatch, db):
    suffix = __import__("uuid").uuid4().hex[:6]
    host, _ = fresh_basic_client(monkeypatch, username=f"h_{suffix}")
    guest, guest_user = fresh_basic_client(monkeypatch, username=f"g_{suffix}")
    add_mutual_friends(host, guest, to_user_id=guest_user["id"])
    guest_pid = _friend_player_id(host, guest_user["id"])
    host_pid = host.post("/api/players", json={"name": "Host"}).json()["id"]
    game_id = host.post("/api/games", json={}).json()["id"]
    begin_game_with_player_ids(host, game_id, [host_pid, guest_pid])

    games = admin_client.get(
        "/api/admin/games",
        params={"participant_email": guest_user["email"], "status": "active"},
    )
    assert games.status_code == 200
    ids = [g["id"] for g in games.json()]
    assert game_id in ids
