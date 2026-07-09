from datetime import datetime, timedelta

import pytest

from app.models import Game, GameStatus
from tests.qa_gameplay import add_mutual_friends, begin_game_with_player_ids, fresh_basic_client


def _friend_player_id(host_client, friend_user_id: int) -> int:
    players = host_client.get("/api/players").json()
    return next(p["id"] for p in players if p.get("linked_user_id") == friend_user_id)


def _set_last_activity(db, game_id: int, hours_ago: float) -> None:
    game = db.get(Game, game_id)
    game.last_activity_at = datetime.utcnow() - timedelta(hours=hours_ago)
    db.commit()


@pytest.mark.integration
def test_stale_active_swept_on_add_player(monkeypatch, db):
    suffix = __import__("uuid").uuid4().hex[:6]
    carol, _ = fresh_basic_client(monkeypatch, username=f"c_{suffix}")
    bob, bob_user = fresh_basic_client(monkeypatch, username=f"b_{suffix}")
    alice, _ = fresh_basic_client(monkeypatch, username=f"a_{suffix}")
    add_mutual_friends(carol, bob, to_user_id=bob_user["id"])
    add_mutual_friends(alice, bob, to_user_id=bob_user["id"])
    bob_pid = _friend_player_id(carol, bob_user["id"])
    carol_host = carol.post("/api/players", json={"name": "Carol"}).json()["id"]
    game1 = carol.post("/api/games", json={}).json()["id"]
    begin_game_with_player_ids(carol, game1, [carol_host, bob_pid])
    _set_last_activity(db, game1, 4)
    bob_pid_a = _friend_player_id(alice, bob_user["id"])
    alice_host = alice.post("/api/players", json={"name": "Alice"}).json()["id"]
    game2 = alice.post("/api/games", json={}).json()["id"]
    assert alice.put(f"/api/games/{game2}/players", json={"player_ids": [alice_host, bob_pid_a]}).status_code == 200
    assert db.get(Game, game1).status == GameStatus.completed


@pytest.mark.integration
def test_participant_abandon_idle_game(monkeypatch, db):
    suffix = __import__("uuid").uuid4().hex[:6]
    host, _ = fresh_basic_client(monkeypatch, username=f"h_{suffix}")
    guest, guest_user = fresh_basic_client(monkeypatch, username=f"g_{suffix}")
    add_mutual_friends(host, guest, to_user_id=guest_user["id"])
    guest_pid = _friend_player_id(host, guest_user["id"])
    host_pid = host.post("/api/players", json={"name": "Host"}).json()["id"]
    game_id = host.post("/api/games", json={}).json()["id"]
    begin_game_with_player_ids(host, game_id, [host_pid, guest_pid])
    _set_last_activity(db, game_id, 4)
    assert guest.post(f"/api/games/{game_id}/abandon").json()["status"] == "completed"
