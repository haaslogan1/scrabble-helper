import pytest

from tests.qa_gameplay import abandon_in_progress_games


def _start_game(client):
    abandon_in_progress_games(client)
    ids = []
    for name in ("P1", "P2"):
        ids.append(client.post("/api/players", json={"name": name}).json()["id"])
    game_id = client.post("/api/games", json={}).json()["id"]
    client.put(f"/api/games/{game_id}/players", json={"player_ids": ids})
    client.post(f"/api/games/{game_id}/begin")
    return game_id, ids


@pytest.mark.integration
def test_live_turn_flow(client):
    game_id, _ = _start_game(client)

    turn = client.post(
        f"/api/games/{game_id}/turns",
        json={"points": 12, "play_type": "score", "timer_elapsed_sec": 45},
    )
    assert turn.status_code == 200
    assert turn.json()["current_player"] == "P1"
    scores = {s["name"]: s["total_score"] for s in turn.json()["standings"]}
    assert scores["Dev User"] == 12

    challenge = client.post(
        f"/api/games/{game_id}/turns",
        json={"play_type": "challenge"},
    )
    assert challenge.status_code == 200
    assert challenge.json()["current_player"] == "P2"
    assert challenge.json()["current_round"] == 1


@pytest.mark.integration
def test_submit_updates_standings_and_advances(client):
    game_id, _ = _start_game(client)
    first = client.post(
        f"/api/games/{game_id}/turns",
        json={"points": 12, "play_type": "score"},
    )
    assert first.status_code == 200
    body = first.json()
    assert body["current_player"] == "P1"
    scores = {s["name"]: s["total_score"] for s in body["standings"]}
    assert scores["Dev User"] == 12

    second = client.post(
        f"/api/games/{game_id}/turns",
        json={"points": 20, "play_type": "score"},
    )
    assert second.status_code == 200
    scores = {s["name"]: s["total_score"] for s in second.json()["standings"]}
    assert scores["Dev User"] == 12
    assert scores["P1"] == 20


@pytest.mark.integration
def test_hidden_leaderboard(client):
    game_id, _ = _start_game(client)
    state = client.get(f"/api/games/{game_id}/state").json()
    for row in state["standings"]:
        assert row["total_score"] is None or state["settings"]["show_live_leaderboard"]
