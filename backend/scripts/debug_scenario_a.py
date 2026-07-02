#!/usr/bin/env python3
"""Step-through scenario A on PostgreSQL for CI diagnostics."""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path
from unittest.mock import patch

backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_dir))

os.environ.setdefault("DEV_AUTH_BYPASS", "true")
os.environ.setdefault("SESSION_SECRET", "test-secret")


def fail(step: str, detail: str) -> None:
    print(f"::error title=scenario_a {step}::{detail}")
    raise SystemExit(1)


def main() -> int:
    if not os.environ.get("DATABASE_URL", "").startswith("postgresql"):
        print("skip: not postgres")
        return 0

    try:
        from tests.conftest import _reset_schema
        from tests.qa_gameplay import (
            add_mutual_friends,
            begin_game_with_player_ids,
            finalize_game,
            fresh_basic_client,
            play_full_game,
            play_turn,
        )

        print("step reset_schema")
        _reset_schema()

        with patch("app.main.run_migrations", lambda: None):
            suffix = uuid.uuid4().hex[:6]
            monkeypatch = __import__("pytest").MonkeyPatch()
            try:
                print("step create users")
                alice, _alice_user = fresh_basic_client(monkeypatch, username=f"alice_{suffix}")
                bob, bob_user = fresh_basic_client(
                    monkeypatch, username=f"bob_{suffix}", name="Bob Friend"
                )
                print("step add mutual friends")
                add_mutual_friends(alice, bob, to_user_id=bob_user["id"])

                players = alice.get("/api/players").json()
                matches = [p for p in players if p.get("linked_user_id") == bob_user["id"]]
                if not matches:
                    fail("friend_player", f"players={players}")
                bob_player_id = matches[0]["id"]
                manual = alice.post("/api/players", json={"name": "Manual Host"}).json()["id"]
                game_id = alice.post("/api/games", json={}).json()["id"]
                begin_game_with_player_ids(alice, game_id, [manual, bob_player_id])

                play_full_game(alice, game_id, player_count=2, rounds=2)
                alice.post(f"/api/games/{game_id}/turns", json={"play_type": "challenge"})
                alice.post(f"/api/games/{game_id}/turns", json={"play_type": "skip"})

                bob_state = bob.get(f"/api/games/{game_id}/state")
                if bob_state.status_code != 200:
                    fail("bob_state", f"status={bob_state.status_code} body={bob_state.text}")
                bob_body = bob_state.json()
                if bob_body.get("role") != "spectator":
                    fail("bob_role", f"role={bob_body.get('role')!r}")

                alice_state = alice.get(f"/api/games/{game_id}/state").json()
                if bob_body["standings"] != alice_state["standings"]:
                    fail("standings", f"bob={bob_body['standings']} alice={alice_state['standings']}")

                denied = bob.post(
                    f"/api/games/{game_id}/turns", json={"points": 5, "play_type": "score"}
                )
                if denied.status_code != 403:
                    fail("deny_turn", f"status={denied.status_code} body={denied.text}")

                play_turn(alice, game_id, 15)
                bob_after = bob.get(f"/api/games/{game_id}/state").json()
                if bob_after["current_round"] < alice_state["current_round"]:
                    fail(
                        "round",
                        f"bob={bob_after['current_round']} alice={alice_state['current_round']}",
                    )

                player_ids = [
                    s["player_id"]
                    for s in alice.get(f"/api/games/{game_id}/state").json()["standings"]
                ]
                finalize_game(alice, game_id, player_ids)

                detail = bob.get(f"/api/games/{game_id}").json()
                if detail.get("status") != "completed":
                    fail("finalize", f"status={detail.get('status')!r}")

                friends_board = alice.get("/api/leaderboard", params={"scope": "friends"})
                if friends_board.status_code != 200:
                    fail("leaderboard", f"status={friends_board.status_code} body={friends_board.text}")
                friend_names = {r["player"] for r in friends_board.json()["games_played"]}
                if "Bob Friend" not in friend_names:
                    fail(
                        "leaderboard_names",
                        f"names={sorted(friend_names)} board={friends_board.json()}",
                    )

                print("scenario_a ok")
                return 0
            finally:
                monkeypatch.undo()
    except SystemExit:
        raise
    except Exception as exc:
        import traceback

        traceback.print_exc()
        fail("exception", f"{type(exc).__name__}: {exc}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
