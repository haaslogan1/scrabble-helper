import uuid

import pytest

from tests.qa_gameplay import (
    accept_friend_request,
    add_friend,
    add_mutual_friends,
    fresh_basic_client,
)


@pytest.mark.integration
def test_friend_request_creates_notification(monkeypatch):
    alice, _ = fresh_basic_client(monkeypatch, username="alice_req1")
    bob, bob_user = fresh_basic_client(monkeypatch, username="bob_req1")

    add_friend(alice, user_id=bob_user["id"])

    notifs = bob.get("/api/notifications")
    assert notifs.status_code == 200
    data = notifs.json()
    assert data["unread_count"] >= 1
    assert any(n["type"] == "friend_request" for n in data["notifications"])

    count = bob.get("/api/notifications/unread-count")
    assert count.json()["unread_count"] >= 1


@pytest.mark.integration
def test_accept_request_creates_mutual_friends_and_linked_player(monkeypatch):
    alice, alice_user = fresh_basic_client(monkeypatch, username=f"alice_{uuid.uuid4().hex[:6]}")
    bob, bob_user = fresh_basic_client(monkeypatch, username=f"bob_{uuid.uuid4().hex[:6]}")

    add_friend(alice, user_id=bob_user["id"])
    incoming = bob.get("/api/friends/requests/incoming").json()
    accept_friend_request(bob, incoming[0]["id"])

    friends = alice.get("/api/friends").json()
    assert any(f["id"] == bob_user["id"] for f in friends)

    players = alice.get("/api/players").json()
    assert any(p.get("linked_user_id") == bob_user["id"] for p in players)

    alice_notifs = alice.get("/api/notifications").json()
    assert any(n["type"] == "friend_request_accepted" for n in alice_notifs["notifications"])


@pytest.mark.integration
def test_deny_request_notifies_sender(monkeypatch):
    alice, _ = fresh_basic_client(monkeypatch, username=f"alice_d_{uuid.uuid4().hex[:6]}")
    bob, bob_user = fresh_basic_client(monkeypatch, username=f"bob_d_{uuid.uuid4().hex[:6]}")

    add_friend(alice, user_id=bob_user["id"])
    incoming = bob.get("/api/friends/requests/incoming").json()
    deny = bob.post(f"/api/friends/requests/{incoming[0]['id']}/deny")
    assert deny.status_code == 200

    alice_notifs = alice.get("/api/notifications").json()
    assert any(n["type"] == "friend_request_declined" for n in alice_notifs["notifications"])


@pytest.mark.integration
def test_search_by_username(monkeypatch):
    alice, _ = fresh_basic_client(monkeypatch, username="searchalice2")
    fresh_basic_client(monkeypatch, username="searchbob2")

    res = alice.get("/api/users/search", params={"q": "searchbo"})
    assert res.status_code == 200
    names = [r["username"] for r in res.json()]
    assert "searchbob2" in names


@pytest.mark.integration
def test_live_game_started_notification(monkeypatch):
    alice, alice_user = fresh_basic_client(monkeypatch, username=f"ahost_{uuid.uuid4().hex[:6]}")
    bob, bob_user = fresh_basic_client(monkeypatch, username=f"bplay_{uuid.uuid4().hex[:6]}")
    add_mutual_friends(alice, bob, to_user_id=bob_user["id"])

    bob_player_id = next(
        p["id"]
        for p in alice.get("/api/players").json()
        if p.get("linked_user_id") == bob_user["id"]
    )
    host_id = alice.post("/api/players", json={"name": "Host"}).json()["id"]
    game_id = alice.post("/api/games", json={}).json()["id"]
    alice.put(f"/api/games/{game_id}/players", json={"player_ids": [host_id, bob_player_id]})
    alice.post(f"/api/games/{game_id}/begin")

    notifs = bob.get("/api/notifications").json()
    live = [n for n in notifs["notifications"] if n["type"] == "live_game_started"]
    assert live
    assert live[0]["payload"]["game_id"] == game_id


@pytest.mark.integration
def test_game_completed_notification(monkeypatch):
    from tests.qa_gameplay import finalize_game, play_full_game

    alice, _ = fresh_basic_client(monkeypatch, username=f"ahost2_{uuid.uuid4().hex[:6]}")
    bob, bob_user = fresh_basic_client(monkeypatch, username=f"bplay2_{uuid.uuid4().hex[:6]}")
    add_mutual_friends(alice, bob, to_user_id=bob_user["id"])

    bob_player_id = next(
        p["id"]
        for p in alice.get("/api/players").json()
        if p.get("linked_user_id") == bob_user["id"]
    )
    host_id = alice.post("/api/players", json={"name": "Host"}).json()["id"]
    game_id = alice.post("/api/games", json={}).json()["id"]
    alice.put(f"/api/games/{game_id}/players", json={"player_ids": [host_id, bob_player_id]})
    alice.post(f"/api/games/{game_id}/begin")
    play_full_game(alice, game_id, player_count=2, rounds=1)
    finalize_game(alice, game_id, [host_id, bob_player_id])

    notifs = bob.get("/api/notifications").json()
    completed = [n for n in notifs["notifications"] if n["type"] == "game_completed"]
    assert completed
    assert completed[0]["payload"]["game_id"] == game_id
