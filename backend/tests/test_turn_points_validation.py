import pytest

from app.scoring import MAX_TURN_POINTS, validate_turn_points
from tests.qa_gameplay import abandon_in_progress_games


@pytest.mark.unit
@pytest.mark.parametrize(
    "value,expected",
    [
        (1, 1),
        (1786, 1786),
        (42, 42),
    ],
)
def test_validate_turn_points_accepts_valid(value, expected):
    assert validate_turn_points(value) == expected


@pytest.mark.unit
@pytest.mark.parametrize(
    "value,message",
    [
        (None, "Enter a point value"),
        (0, "at least 1"),
        (-5, "at least 1"),
        (12.5, "whole number"),
        (1787, "cannot exceed"),
        ("abc", "positive whole number"),
    ],
)
def test_validate_turn_points_rejects_invalid(value, message):
    with pytest.raises(ValueError) as exc:
        validate_turn_points(value)  # type: ignore[arg-type]
    assert message in str(exc.value).lower() or message in str(exc.value)


@pytest.mark.unit
def test_max_turn_points_constant():
    assert MAX_TURN_POINTS == 1786


@pytest.mark.integration
def test_invalid_points_do_not_advance_turn(client):
    abandon_in_progress_games(client)
    ids = []
    for name in ("P1", "P2"):
        ids.append(client.post("/api/players", json={"name": name}).json()["id"])
    game_id = client.post("/api/games", json={}).json()["id"]
    client.put(f"/api/games/{game_id}/players", json={"player_ids": ids})
    client.post(f"/api/games/{game_id}/begin")

    invalid = client.post(
        f"/api/games/{game_id}/turns",
        json={"points": 0, "play_type": "score"},
    )
    assert invalid.status_code == 400
    assert "at least 1" in invalid.json()["detail"].lower()

    state = client.get(f"/api/games/{game_id}/state").json()
    assert state["current_player"] == "Dev User"
    scores = {s["name"]: s["total_score"] for s in state["standings"]}
    assert scores["Dev User"] == 0.0

    over = client.post(
        f"/api/games/{game_id}/turns",
        json={"points": MAX_TURN_POINTS + 1, "play_type": "score"},
    )
    assert over.status_code == 400
    state = client.get(f"/api/games/{game_id}/state").json()
    assert state["current_player"] == "Dev User"

    valid = client.post(
        f"/api/games/{game_id}/turns",
        json={"points": 15, "play_type": "score"},
    )
    assert valid.status_code == 200
    assert valid.json()["current_player"] == "P1"
    scores = {s["name"]: s["total_score"] for s in valid.json()["standings"]}
    assert scores["Dev User"] == 15
