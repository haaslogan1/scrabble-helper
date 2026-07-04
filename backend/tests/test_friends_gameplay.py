import uuid

import pytest

from tests.qa_gameplay import (
    accept_friend_request,
    add_friend,
    add_mutual_friends,
    begin_game_with_player_ids,
    connect_game_watch_ws,
    finalize_game,
    fresh_basic_client,
    play_full_game,
    play_turn,
)


def _friend_player_id(host_client, friend_user_id: int) -> int:
    players = host_client.get("/api/players").json()
    return next(p["id"] for p in players if p.get("linked_user_id") == friend_user_id)


@pytest.mark.integration
def test_scenario_a_mutual_live_spectate(monkeypatch):
    suffix = uuid.uuid4().hex[:6]
    alice, alice_user = fresh_basic_client(monkeypatch, username=f"alice_{suffix}")
    bob, bob_user = fresh_basic_client(monkeypatch, username=f"bob_{suffix}", name="Bob Friend")
    add_mutual_friends(alice, bob, to_user_id=bob_user["id"])

    bob_player_id = _friend_player_id(alice, bob_user["id"])
    manual = alice.post("/api/players", json={"name": "Manual Host"}).json()["id"]
    game_id = alice.post("/api/games", json={}).json()["id"]
    begin_game_with_player_ids(alice, game_id, [manual, bob_player_id])

    play_full_game(alice, game_id, player_count=2, rounds=2)
    alice.post(f"/api/games/{game_id}/turns", json={"play_type": "challenge"})
    alice.post(f"/api/games/{game_id}/turns", json={"play_type": "skip"})

    bob_state = bob.get(f"/api/games/{game_id}/state").json()
    assert bob_state["role"] == "spectator"
    alice_state = alice.get(f"/api/games/{game_id}/state").json()
    assert bob_state["standings"] == alice_state["standings"]

    denied = bob.post(f"/api/games/{game_id}/turns", json={"points": 5, "play_type": "score"})
    assert denied.status_code == 403

    with connect_game_watch_ws(bob, game_id) as ws:
        snapshot = ws.receive_json()
        assert snapshot["current_round"] == alice_state["current_round"]
        play_turn(alice, game_id, 15)
        update = ws.receive_json()
        assert update["current_round"] >= snapshot["current_round"]

    player_ids = [s["player_id"] for s in alice.get(f"/api/games/{game_id}/state").json()["standings"]]
    finalize_game(alice, game_id, player_ids)

    detail = bob.get(f"/api/games/{game_id}").json()
    assert detail["status"] == "completed"

    friends_board = alice.get("/api/leaderboard", params={"scope": "friends"}).json()
    friend_names = {r["player"] for r in friends_board["games_played"]}
    assert "Bob Friend" in friend_names


@pytest.mark.integration
def test_scenario_b_two_spectators(monkeypatch):
    suffix = uuid.uuid4().hex[:6]
    alice, alice_user = fresh_basic_client(monkeypatch, username=f"ahost_{suffix}")
    bob, bob_user = fresh_basic_client(monkeypatch, username=f"bwatch_{suffix}")
    carol, carol_user = fresh_basic_client(monkeypatch, username=f"cwatch_{suffix}")

    add_mutual_friends(alice, bob, to_user_id=bob_user["id"])
    add_mutual_friends(alice, carol, to_user_id=carol_user["id"])

    bob_pid = _friend_player_id(alice, bob_user["id"])
    carol_pid = _friend_player_id(alice, carol_user["id"])
    host_pid = alice.post("/api/players", json={"name": "Host"}).json()["id"]
    game_id = alice.post("/api/games", json={}).json()["id"]
    begin_game_with_player_ids(alice, game_id, [host_pid, bob_pid, carol_pid])

    play_full_game(alice, game_id, player_count=3, rounds=2)

    bob_view = bob.get(f"/api/games/{game_id}/state").json()
    carol_view = carol.get(f"/api/games/{game_id}/state").json()
    assert bob_view["current_player"] == carol_view["current_player"]
    assert bob_view["role"] == carol_view["role"] == "spectator"

    denied = carol.post(f"/api/games/{game_id}/turns", json={"points": 1, "play_type": "score"})
    assert denied.status_code == 403


@pytest.mark.integration
def test_scenario_c_non_participant_cannot_spectate(monkeypatch):
    suffix = uuid.uuid4().hex[:6]
    alice, _ = fresh_basic_client(monkeypatch, username=f"ahost2_{suffix}")
    bob, bob_user = fresh_basic_client(monkeypatch, username=f"bout2_{suffix}")
    add_mutual_friends(alice, bob, to_user_id=bob_user["id"])

    manual_ids = []
    for name in ("OnlyA", "OnlyB"):
        manual_ids.append(alice.post("/api/players", json={"name": name}).json()["id"])
    game_id = alice.post("/api/games", json={}).json()["id"]
    begin_game_with_player_ids(alice, game_id, manual_ids)

    assert bob.get(f"/api/games/{game_id}/state").status_code in (403, 404)
    with pytest.raises(Exception):
        with connect_game_watch_ws(bob, game_id):
            pass


@pytest.mark.integration
def test_scenario_d_one_way_blocks_live_game(monkeypatch):
    suffix = uuid.uuid4().hex[:6]
    alice, _ = fresh_basic_client(monkeypatch, username=f"ahost3_{suffix}")
    _, bob_user = fresh_basic_client(monkeypatch, username=f"bonly3_{suffix}", name="Bob Solo")

    add_friend(alice, user_id=bob_user["id"])
    # Bob does not accept — no linked friend player on Alice's roster
    host_pid = alice.post("/api/players", json={"name": "Alice Manual"}).json()["id"]
    manual_bob = alice.post("/api/players", json={"name": "Bob Solo Manual"}).json()["id"]
    game_id = alice.post("/api/games", json={}).json()["id"]
    attach = alice.put(f"/api/games/{game_id}/players", json={"player_ids": [host_pid, manual_bob]})
    assert attach.status_code == 200
    begin = alice.post(f"/api/games/{game_id}/begin")
    assert begin.status_code == 200


@pytest.mark.integration
def test_scenario_d_after_mutual_succeeds(monkeypatch):
    suffix = uuid.uuid4().hex[:6]
    alice, _ = fresh_basic_client(monkeypatch, username=f"ahost4_{suffix}")
    bob, bob_user = fresh_basic_client(monkeypatch, username=f"bob4_{suffix}")
    add_friend(alice, user_id=bob_user["id"])

    host_pid = alice.post("/api/players", json={"name": "Alice"}).json()["id"]
    game_id = alice.post("/api/games", json={}).json()["id"]
    # Owner is auto-included, so one manual opponent is enough to attach
    attach = alice.put(f"/api/games/{game_id}/players", json={"player_ids": [host_pid]})
    assert attach.status_code == 200
    assert len(attach.json()["standings"]) == 2

    incoming = bob.get("/api/friends/requests/incoming").json()
    accept_friend_request(bob, incoming[0]["id"])
    bob_pid = _friend_player_id(alice, bob_user["id"])
    begin_game_with_player_ids(alice, game_id, [host_pid, bob_pid])
    assert alice.get(f"/api/games/{game_id}/state").json()["status"] == "active"


@pytest.mark.integration
def test_scenario_e_mutual_removed_before_begin(monkeypatch):
    suffix = uuid.uuid4().hex[:6]
    alice, alice_user = fresh_basic_client(monkeypatch, username=f"ahost5_{suffix}")
    bob, bob_user = fresh_basic_client(monkeypatch, username=f"bob5_{suffix}")
    add_mutual_friends(alice, bob, to_user_id=bob_user["id"])

    bob_pid = _friend_player_id(alice, bob_user["id"])
    host_pid = alice.post("/api/players", json={"name": "Alice"}).json()["id"]
    game_id = alice.post("/api/games", json={}).json()["id"]
    attach = alice.put(
        f"/api/games/{game_id}/players", json={"player_ids": [host_pid, bob_pid]}
    )
    assert attach.status_code == 200
    assert len(attach.json()["standings"]) == 3

    alice.delete(f"/api/friends/{bob_user['id']}")
    state = alice.get(f"/api/games/{game_id}/state").json()
    roster_ids = {s["player_id"] for s in state["standings"]}
    assert bob_pid not in roster_ids

    begin = alice.post(f"/api/games/{game_id}/begin")
    assert begin.status_code == 200
    assert len(begin.json()["standings"]) == 2


@pytest.mark.integration
def test_scenario_f_user_already_in_live_game(monkeypatch):
    suffix = uuid.uuid4().hex[:6]
    carol, _ = fresh_basic_client(monkeypatch, username=f"carol6_{suffix}")
    bob, bob_user = fresh_basic_client(monkeypatch, username=f"bob6_{suffix}")
    alice, _ = fresh_basic_client(monkeypatch, username=f"alice6_{suffix}")

    add_mutual_friends(carol, bob, to_user_id=bob_user["id"])
    add_mutual_friends(alice, bob, to_user_id=bob_user["id"])

    bob_pid_carol = _friend_player_id(carol, bob_user["id"])
    carol_host = carol.post("/api/players", json={"name": "Carol"}).json()["id"]
    game1 = carol.post("/api/games", json={}).json()["id"]
    begin_game_with_player_ids(carol, game1, [carol_host, bob_pid_carol])

    bob_pid_alice = _friend_player_id(alice, bob_user["id"])
    alice_host = alice.post("/api/players", json={"name": "Alice"}).json()["id"]
    game2 = alice.post("/api/games", json={}).json()["id"]
    blocked = alice.put(
        f"/api/games/{game2}/players", json={"player_ids": [alice_host, bob_pid_alice]}
    )
    assert blocked.status_code == 400
    assert "already playing a live game" in blocked.json()["detail"].lower()

    finalize_game(carol, game1, [carol_host, bob_pid_carol])

    begin_game_with_player_ids(alice, game2, [alice_host, bob_pid_alice])
    assert alice.get(f"/api/games/{game2}/state").json()["status"] == "active"
