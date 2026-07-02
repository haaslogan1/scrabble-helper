import pytest

from app.scoring import assign_placements, PlayerScore


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


@pytest.mark.integration
def test_leaderboard_scope_filters(auth_client):
    manual_ids = []
    for name in ("ManualA", "ManualB"):
        manual_ids.append(auth_client.post("/api/players", json={"name": name}).json()["id"])

    game_id = auth_client.post("/api/games", json={}).json()["id"]
    auth_client.put(f"/api/games/{game_id}/players", json={"player_ids": manual_ids})
    auth_client.post(f"/api/games/{game_id}/begin")
    auth_client.post(f"/api/games/{game_id}/turns", json={"points": 10, "play_type": "score"})
    auth_client.post(f"/api/games/{game_id}/turns", json={"points": 20, "play_type": "score"})
    auth_client.post(f"/api/games/{game_id}/end")
    auth_client.post(f"/api/games/{game_id}/finalize", json={"rack_adjustments": {}})

    all_board = auth_client.get("/api/leaderboard", params={"scope": "all"}).json()
    manual_board = auth_client.get("/api/leaderboard", params={"scope": "manual"}).json()
    friends_board = auth_client.get("/api/leaderboard", params={"scope": "friends"}).json()

    all_names = {r["player"] for r in all_board["games_played"]}
    manual_names = {r["player"] for r in manual_board["games_played"]}
    assert "ManualA" in all_names
    assert manual_names == {"ManualA", "ManualB"}
    assert friends_board["games_played"] == []
