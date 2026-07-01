import pytest


def _create_players(client):
    ids = []
    for name in ("Alice", "Bob", "Carol"):
        resp = client.post("/api/players", json={"name": name})
        ids.append(resp.json()["id"])
    return ids


@pytest.mark.integration
def test_game_setup_flow(client):
    player_ids = _create_players(client)

    game = client.post(
        "/api/games",
        json={"settings": {"minutes_per_turn": 5, "input_mode": "points", "show_live_leaderboard": False}},
    )
    assert game.status_code == 200
    game_id = game.json()["id"]

    attach = client.put(f"/api/games/{game_id}/players", json={"player_ids": player_ids})
    assert attach.status_code == 200

    random_first = client.post(f"/api/games/{game_id}/random-first")
    assert random_first.status_code == 200

    reorder = client.post(
        f"/api/games/{game_id}/turn-order",
        json={"player_ids": [player_ids[1], player_ids[0], player_ids[2]]},
    )
    assert reorder.status_code == 200

    begin = client.post(f"/api/games/{game_id}/begin")
    assert begin.status_code == 200
    assert begin.json()["status"] == "active"
