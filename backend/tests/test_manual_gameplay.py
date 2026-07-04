import pytest

from tests.qa_gameplay import finalize_game, play_full_game, setup_and_begin_game


@pytest.mark.integration
def test_manual_only_gameplay_and_leaderboard_scopes(auth_client):
    game_id = setup_and_begin_game(auth_client, ["Manual One", "Manual Two"])
    play_full_game(auth_client, game_id, rounds=2)
    auth_client.post(f"/api/games/{game_id}/turns", json={"play_type": "challenge"})
    auth_client.post(f"/api/games/{game_id}/turns", json={"play_type": "skip"})

    player_ids = [p["id"] for p in auth_client.get("/api/players").json()]
    finalize_game(auth_client, game_id, player_ids)

    all_board = auth_client.get("/api/leaderboard", params={"scope": "all"}).json()
    manual_board = auth_client.get("/api/leaderboard", params={"scope": "manual"}).json()
    friends_board = auth_client.get("/api/leaderboard", params={"scope": "friends"}).json()

    all_names = {r["player"] for r in all_board["games_played"]}
    manual_names = {r["player"] for r in manual_board["games_played"]}
    assert "Manual One" in all_names and "Manual Two" in all_names
    assert manual_names == {"Manual One", "Manual Two"}
    friends_names = {r["player"] for r in friends_board["games_played"]}
    assert friends_names == {"QA User"}


@pytest.mark.integration
def test_second_user_cannot_access_manual_live_game(monkeypatch, auth_client):
    game_id = setup_and_begin_game(auth_client, ["Host P1", "Host P2"])

    from tests.qa_gameplay import fresh_basic_client

    other, _ = fresh_basic_client(monkeypatch)
    assert other.get(f"/api/games/{game_id}/state").status_code in (403, 404)
