import pytest

from app.scoring import (
    MAX_RACK_ADJUSTMENT,
    MIN_RACK_ADJUSTMENT,
    validate_rack_adjustment,
)
from tests.qa_gameplay import abandon_in_progress_games, setup_and_begin_game


@pytest.mark.unit
@pytest.mark.parametrize(
    "value,expected",
    [
        (-12, -12),
        (0, 0),
        (-70, -70),
        (-1, -1),
    ],
)
def test_validate_rack_adjustment_accepts_valid(value, expected):
    assert validate_rack_adjustment(value) == expected


@pytest.mark.unit
@pytest.mark.parametrize(
    "value,message",
    [
        (-71, "between -70 and 0"),
        (1, "between -70 and 0"),
        (-1000, "between -70 and 0"),
        (-12.5, "whole number"),
        ("abc", "whole number"),
        (True, "whole number"),
    ],
)
def test_validate_rack_adjustment_rejects_invalid(value, message):
    with pytest.raises(ValueError) as exc:
        validate_rack_adjustment(value)  # type: ignore[arg-type]
    assert message in str(exc.value).lower() or message in str(exc.value)


@pytest.mark.unit
def test_rack_adjustment_constants():
    assert MIN_RACK_ADJUSTMENT == -70
    assert MAX_RACK_ADJUSTMENT == 0


def _game_in_ending(client):
    abandon_in_progress_games(client)
    game_id = setup_and_begin_game(client, ["R1", "R2"])
    attach = client.get(f"/api/games/{game_id}/state").json()
    by_name = {s["name"]: s["player_id"] for s in attach["standings"]}
    client.post(f"/api/games/{game_id}/end")
    return game_id, by_name


@pytest.mark.integration
@pytest.mark.parametrize(
    "adjustments,expected_status",
    [
        ({"R1": -12, "R2": 0}, 200),
        ({"R1": -70, "R2": 0}, 200),
        ({"R1": 0, "R2": 0}, 200),
        ({"R1": -71}, 400),
        ({"R1": 1}, 400),
        ({"R1": -1000}, 400),
        ({"R1": -12.5}, 400),
    ],
)
def test_finalize_rack_adjustment_validation(client, adjustments, expected_status):
    game_id, by_name = _game_in_ending(client)
    payload = {
        str(by_name[name]): value
        for name, value in adjustments.items()
    }
    res = client.post(
        f"/api/games/{game_id}/finalize",
        json={"rack_adjustments": payload},
    )
    assert res.status_code == expected_status
    if expected_status == 200 and adjustments.get("R1") == -12:
        detail = client.get(f"/api/games/{game_id}").json()
        r1 = next(p for p in detail["players"] if p["name"] == "R1")
        assert r1["rack_adjustment"] == -12


@pytest.mark.integration
def test_finalize_defaults_missing_player_to_zero(client):
    game_id, by_name = _game_in_ending(client)
    res = client.post(
        f"/api/games/{game_id}/finalize",
        json={"rack_adjustments": {str(by_name["R1"]): -5}},
    )
    assert res.status_code == 200
    detail = client.get(f"/api/games/{game_id}").json()
    r2 = next(p for p in detail["players"] if p["name"] == "R2")
    assert r2["rack_adjustment"] == 0
