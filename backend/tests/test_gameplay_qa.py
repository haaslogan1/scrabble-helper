import pytest

from tests.qa_gameplay import (
    finalize_game,
    play_full_game,
    play_turn,
    setup_and_begin_game,
)


@pytest.mark.integration
def test_full_game_flow_points_mode(auth_client):
    game_id = setup_and_begin_game(
        auth_client,
        ["Alice", "Bob"],
        settings={
            "minutes_per_turn": 3,
            "input_mode": "points",
            "show_live_leaderboard": True,
        },
    )
    play_full_game(auth_client, game_id, player_count=2, rounds=2)
    player_ids = [p["id"] for p in auth_client.get("/api/players").json()]
    finalize_game(auth_client, game_id, player_ids)

    detail = auth_client.get(f"/api/games/{game_id}")
    assert detail.status_code == 200
    assert detail.json()["status"] == "completed"

    listing = auth_client.get("/api/games", params={"status": "completed"})
    assert any(g["id"] == game_id for g in listing.json())

    board = auth_client.get("/api/leaderboard")
    assert board.status_code == 200
    assert "total_points" in board.json()


@pytest.mark.integration
def test_challenge_and_skip(auth_client):
    game_id = setup_and_begin_game(auth_client, ["C1", "C2"])
    ch = auth_client.post(f"/api/games/{game_id}/turns", json={"play_type": "challenge"})
    assert ch.status_code == 200
    sk = auth_client.post(f"/api/games/{game_id}/turns", json={"play_type": "skip"})
    assert sk.status_code == 200


@pytest.mark.integration
def test_hidden_leaderboard_during_play(auth_client):
    game_id = setup_and_begin_game(
        auth_client,
        ["H1", "H2"],
        settings={"show_live_leaderboard": False},
    )
    res = play_turn(auth_client, game_id, 10)
    assert res.status_code == 200
    for row in res.json()["standings"]:
        assert row["total_score"] is None
