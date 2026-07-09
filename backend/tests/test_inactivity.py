from datetime import datetime, timedelta

import pytest

from app.models import Game, GameStatus
from tests.qa_gameplay import setup_and_begin_game


def _set_last_activity(db, game_id: int, minutes_ago: float) -> None:
    game = db.get(Game, game_id)
    assert game is not None
    game.last_activity_at = datetime.utcnow() - timedelta(minutes=minutes_ago)
    db.commit()


@pytest.mark.integration
def test_inactivity_warning_after_176_minutes(client, db):
    game_id = setup_and_begin_game(client, ["A1", "B1"])
    _set_last_activity(db, game_id, 176)

    state = client.get(f"/api/games/{game_id}/state")
    assert state.status_code == 200
    body = state.json()
    assert body["inactivity_warning"] is True
    assert body["status"] == "active"


@pytest.mark.integration
def test_no_inactivity_warning_before_120_minutes(client, db):
    game_id = setup_and_begin_game(client, ["A2", "B2"])
    _set_last_activity(db, game_id, 120)

    state = client.get(f"/api/games/{game_id}/state")
    assert state.status_code == 200
    assert state.json()["inactivity_warning"] is False


@pytest.mark.integration
def test_ack_inactivity_clears_warning(client, db):
    game_id = setup_and_begin_game(client, ["A3", "B3"])
    _set_last_activity(db, game_id, 176)

    ack = client.post(f"/api/games/{game_id}/ack-inactivity")
    assert ack.status_code == 200
    assert ack.json()["inactivity_warning"] is False


@pytest.mark.integration
def test_auto_finish_after_181_minutes(client, db):
    game_id = setup_and_begin_game(client, ["A4", "B4"])
    _set_last_activity(db, game_id, 181)

    state = client.get(f"/api/games/{game_id}/state")
    assert state.status_code == 200
    assert state.json()["status"] == "completed"

    game = db.get(Game, game_id)
    assert game is not None
    assert game.status == GameStatus.completed
    for gp in game.game_players:
        assert gp.rack_adjustment == 0.0
