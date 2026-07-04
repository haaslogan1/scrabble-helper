import pytest

from tests.qa_gameplay import abandon_in_progress_games


@pytest.mark.integration
def test_end_finalize_and_list(client):
    abandon_in_progress_games(client)
    ids = []
    for name in ("W1", "W2"):
        ids.append(client.post("/api/players", json={"name": name}).json()["id"])
    game_id = client.post("/api/games", json={}).json()["id"]
    attach = client.put(f"/api/games/{game_id}/players", json={"player_ids": ids})
    assert attach.status_code == 200
    by_name = {s["name"]: s["player_id"] for s in attach.json()["standings"]}
    client.post(f"/api/games/{game_id}/begin")

    client.post(f"/api/games/{game_id}/turns", json={"points": 10, "play_type": "score"})
    client.post(f"/api/games/{game_id}/turns", json={"points": 100, "play_type": "score"})
    client.post(f"/api/games/{game_id}/turns", json={"points": 80, "play_type": "score"})

    client.post(f"/api/games/{game_id}/end")
    finalize = client.post(
        f"/api/games/{game_id}/finalize",
        json={
            "rack_adjustments": {
                str(by_name["W1"]): -5,
                str(by_name["W2"]): 0,
            }
        },
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
