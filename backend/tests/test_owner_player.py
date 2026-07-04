import pytest


@pytest.mark.integration
def test_owner_auto_added_with_single_opponent(auth_client):
    bob = auth_client.post("/api/players", json={"name": "Bob"})
    assert bob.status_code == 200
    bob_id = bob.json()["id"]

    game = auth_client.post("/api/games", json={})
    assert game.status_code == 200
    game_id = game.json()["id"]

    attach = auth_client.put(f"/api/games/{game_id}/players", json={"player_ids": [bob_id]})
    assert attach.status_code == 200
    state = attach.json()
    roster_ids = {s["player_id"] for s in state["standings"]}
    assert len(roster_ids) == 2

    players = auth_client.get("/api/players").json()
    self_players = [p for p in players if p.get("is_self")]
    assert len(self_players) == 1
    assert self_players[0]["id"] in roster_ids

    begin = auth_client.post(f"/api/games/{game_id}/begin")
    assert begin.status_code == 200
    assert begin.json()["status"] == "active"


@pytest.mark.integration
def test_owner_player_record_reused(auth_client):
    bob_id = auth_client.post("/api/players", json={"name": "Bob"}).json()["id"]

    game1 = auth_client.post("/api/games", json={}).json()["id"]
    auth_client.put(f"/api/games/{game1}/players", json={"player_ids": [bob_id]})
    self_id_first = next(
        p["id"] for p in auth_client.get("/api/players").json() if p.get("is_self")
    )

    game2 = auth_client.post("/api/games", json={}).json()["id"]
    auth_client.put(f"/api/games/{game2}/players", json={"player_ids": [bob_id]})
    self_id_second = next(
        p["id"] for p in auth_client.get("/api/players").json() if p.get("is_self")
    )

    assert self_id_first == self_id_second
