import pytest

from tests.qa_gameplay import abandon_in_progress_games


def _create_players(client):
    ids = []
    for name in ("Alice", "Bob", "Carol"):
        resp = client.post("/api/players", json={"name": name})
        ids.append(resp.json()["id"])
    return ids


@pytest.mark.integration
def test_game_setup_flow(client):
    abandon_in_progress_games(client)
    player_ids = _create_players(client)

    game = client.post(
        "/api/games",
        json={"settings": {"minutes_per_turn": 5, "input_mode": "points", "show_live_leaderboard": False}},
    )
    assert game.status_code == 200
    game_id = game.json()["id"]

    attach = client.put(f"/api/games/{game_id}/players", json={"player_ids": player_ids})
    assert attach.status_code == 200
    roster_ids = [s["player_id"] for s in attach.json()["standings"]]
    owner_id = next(pid for pid in roster_ids if pid not in player_ids)

    random_first = client.post(f"/api/games/{game_id}/random-first")
    assert random_first.status_code == 200

    reorder = client.post(
        f"/api/games/{game_id}/turn-order",
        json={"player_ids": [player_ids[1], player_ids[0], player_ids[2], owner_id]},
    )
    assert reorder.status_code == 200

    begin = client.post(f"/api/games/{game_id}/begin")
    assert begin.status_code == 200
    assert begin.json()["status"] == "active"
