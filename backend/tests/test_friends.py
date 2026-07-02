import uuid

import pytest

from tests.qa_gameplay import (
    accept_friend_request,
    add_friend,
    add_mutual_friends,
    fresh_basic_client,
)


@pytest.mark.integration
def test_friend_request_pending_until_accept(monkeypatch):
    alice, _ = fresh_basic_client(monkeypatch, username="alice1")
    bob, bob_user = fresh_basic_client(monkeypatch, username="bob1")

    add_friend(alice, user_id=bob_user["id"])
    players = alice.get("/api/players").json()
    assert not any(p.get("linked_user_id") == bob_user["id"] for p in players)

    incoming = bob.get("/api/friends/requests/incoming").json()
    accept_friend_request(bob, incoming[0]["id"])
    players = alice.get("/api/players").json()
    assert any(p.get("linked_user_id") == bob_user["id"] for p in players)


@pytest.mark.integration
def test_search_by_username(monkeypatch):
    alice, _ = fresh_basic_client(monkeypatch, username="searchalice")
    fresh_basic_client(monkeypatch, username="searchbob")

    res = alice.get("/api/users/search", params={"q": "searchbo"})
    assert res.status_code == 200
    names = [r["username"] for r in res.json()]
    assert "searchbob" in names


@pytest.mark.integration
def test_mutual_flag_on_friend_list(monkeypatch):
    alice, _ = fresh_basic_client(monkeypatch, username=f"alice_{uuid.uuid4().hex[:6]}")
    bob, bob_user = fresh_basic_client(monkeypatch, username=f"bob_{uuid.uuid4().hex[:6]}")

    add_friend(alice, user_id=bob_user["id"])
    incoming = bob.get("/api/friends/requests/incoming").json()
    accept_friend_request(bob, incoming[0]["id"])

    friends = alice.get("/api/friends").json()
    bob_entry = next(f for f in friends if f["id"] == bob_user["id"])
    assert bob_entry["mutual"] is True


@pytest.mark.integration
def test_remove_friend_clears_linked_player(monkeypatch):
    alice, _ = fresh_basic_client(monkeypatch, username=f"alice_rm_{uuid.uuid4().hex[:6]}")
    bob, bob_user = fresh_basic_client(monkeypatch, username=f"bob_rm_{uuid.uuid4().hex[:6]}")
    add_mutual_friends(alice, bob, to_user_id=bob_user["id"])

    assert any(p.get("linked_user_id") == bob_user["id"] for p in alice.get("/api/players").json())
    res = alice.delete(f"/api/friends/{bob_user['id']}")
    assert res.status_code == 200
    assert not any(p.get("linked_user_id") == bob_user["id"] for p in alice.get("/api/players").json())
