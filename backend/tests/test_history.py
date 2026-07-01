import pytest


@pytest.mark.integration
def test_end_finalize_and_list(client):
    ids = []
    for name in ("W1", "W2"):
        ids.append(client.post("/api/players", json={"name": name}).json()["id"])
    game_id = client.post("/api/games", json={}).json()["id"]
    client.put(f"/api/games/{game_id}/players", json={"player_ids": ids})
    client.post(f"/api/games/{game_id}/begin")

    client.post(f"/api/games/{game_id}/turns", json={"points": 100, "play_type": "score"})
    client.post(f"/api/games/{game_id}/turns", json={"points": 80, "play_type": "score"})

    client.post(f"/api/games/{game_id}/end")
    finalize = client.post(
        f"/api/games/{game_id}/finalize",
        json={"rack_adjustments": {str(ids[0]): -5, str(ids[1]): 0}},
    )
    assert finalize.status_code == 200
    assert finalize.json()["status"] == "completed"
    assert finalize.json()["winner"] == "W1"

    listing = client.get("/api/games", params={"status": "completed"})
    assert listing.status_code == 200
    assert any(g["id"] == game_id for g in listing.json())

    detail = client.get(f"/api/games/{game_id}")
    assert detail.status_code == 200
    assert detail.json()["winner"] == "W1"
