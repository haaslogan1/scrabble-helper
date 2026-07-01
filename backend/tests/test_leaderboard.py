import pytest

from app.scoring import assign_placements, PlayerScore, score_from_word


@pytest.mark.unit
def test_assign_placements_tie():
    players = [
        PlayerScore(player_id=1, name="A", total_score=100),
        PlayerScore(player_id=2, name="B", total_score=100),
        PlayerScore(player_id=3, name="C", total_score=50),
    ]
    assign_placements(players)
    assert players[0].placement == 1
    assert players[1].placement == 1
    assert players[2].placement == 3


@pytest.mark.unit
def test_score_from_word():
    assert score_from_word("quiz") == 22


@pytest.mark.integration
def test_leaderboard(client):
    ids = []
    for name in ("L1", "L2"):
        ids.append(client.post("/api/players", json={"name": name}).json()["id"])
    game_id = client.post("/api/games", json={}).json()["id"]
    client.put(f"/api/games/{game_id}/players", json={"player_ids": ids})
    client.post(f"/api/games/{game_id}/begin")
    client.post(f"/api/games/{game_id}/turns", json={"points": 50, "play_type": "score"})
    client.post(f"/api/games/{game_id}/turns", json={"points": 30, "play_type": "score"})
    client.post(f"/api/games/{game_id}/end")
    client.post(f"/api/games/{game_id}/finalize", json={"rack_adjustments": {}})

    board = client.get("/api/leaderboard")
    assert board.status_code == 200
    keys = {
        "win_leaderboard",
        "total_points",
        "avg_points_per_play",
        "avg_total_per_game",
        "lost_challenges_or_skipped_turns",
        "games_played",
    }
    assert set(board.json().keys()) == keys
