#!/usr/bin/env python3
"""Continuous QA agent for scrabble-helper (production API)."""

from __future__ import annotations

import json
import os
import random
import sys
import time
import traceback
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import httpx

BASE_URL = os.environ.get("QA_BASE_URL", "https://scrabble-helper.fly.dev").rstrip("/")
DEFAULT_PASSWORD = os.environ.get("QA_BASIC_PASSWORD", "QaTestPass1")
LOOP_SLEEP_SEC = int(os.environ.get("QA_LOOP_SLEEP_SEC", "30"))
README = Path(__file__).resolve().parents[2] / "README.md"
REPORTER = "QA agent"


@dataclass
class Issue:
    area: str
    summary: str
    steps: str


@dataclass
class QARun:
    email: str
    issues: list[Issue] = field(default_factory=list)


class QAClient:
    def __init__(self) -> None:
        self.http = httpx.Client(base_url=BASE_URL, timeout=60.0, follow_redirects=True)

    def close(self) -> None:
        self.http.close()

    def register(self, email: str, password: str = DEFAULT_PASSWORD) -> dict:
        res = self.http.post(
            "/auth/register",
            json={"email": email, "password": password, "name": "QA Agent"},
        )
        if res.status_code == 400 and "verification" in res.text.lower():
            raise RuntimeError(
                "Email verification required on target; use a deploy with direct /auth/register "
                "or set QA_BASE_URL to a test environment."
            )
        res.raise_for_status()
        return res.json()

    def login(self, email: str, password: str = DEFAULT_PASSWORD) -> dict:
        res = self.http.post("/auth/login", json={"email": email, "password": password})
        res.raise_for_status()
        return res.json()

    def create_players(self, names: list[str]) -> list[int]:
        ids = []
        for name in names:
            res = self.http.post("/api/players", json={"name": name})
            res.raise_for_status()
            ids.append(res.json()["id"])
        return ids

    def begin_game(self, player_names: list[str], settings: dict | None = None) -> int:
        ids = self.create_players(player_names)
        body: dict = {}
        if settings:
            body["settings"] = settings
        game = self.http.post("/api/games", json=body)
        game.raise_for_status()
        game_id = game.json()["id"]
        attach = self.http.put(f"/api/games/{game_id}/players", json={"player_ids": ids})
        attach.raise_for_status()
        begin = self.http.post(f"/api/games/{game_id}/begin")
        begin.raise_for_status()
        return game_id

    def turn(self, game_id: int, **payload) -> httpx.Response:
        return self.http.post(f"/api/games/{game_id}/turns", json=payload)

    def game_state(self, game_id: int) -> dict:
        res = self.http.get(f"/api/games/{game_id}/state")
        res.raise_for_status()
        return res.json()

    def end_and_finalize(self, game_id: int, player_ids: list[int]) -> dict:
        self.http.post(f"/api/games/{game_id}/end").raise_for_status()
        racks = {str(pid): 0 for pid in player_ids}
        fin = self.http.post(
            f"/api/games/{game_id}/finalize",
            json={"rack_adjustments": racks},
        )
        fin.raise_for_status()
        return fin.json()


def record_issue(run: QARun, area: str, summary: str, steps: str) -> None:
    for existing in run.issues:
        if existing.summary == summary:
            return
    run.issues.append(Issue(area=area, summary=summary, steps=steps))
    print(f"ISSUE [{area}] {summary}")


def append_readme_issues(run: QARun) -> None:
    if not run.issues or not README.exists():
        return
    text = README.read_text(encoding="utf-8")
    marker = "| Date | Reporter | Area | Summary | Steps to reproduce |"
    if marker not in text:
        return
    existing_summaries = set()
    for line in text.splitlines():
        if line.startswith("| 20") and "| QA agent |" in line:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 5:
                existing_summaries.add(parts[4])
    rows = []
    today = date.today().isoformat()
    for issue in run.issues:
        if issue.summary in existing_summaries:
            continue
        rows.append(
            f"| {today} | {REPORTER} | {issue.area} | {issue.summary} | {issue.steps} |"
        )
    if not rows:
        return
    lines = text.splitlines()
    insert_at = next(i for i, line in enumerate(lines) if line.strip() == marker) + 2
    for offset, row in enumerate(rows):
        lines.insert(insert_at + offset, row)
    README.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Logged {len(rows)} issue(s) to README.md")


def scenario_full_game(client: QAClient, run: QARun, player_count: int, rounds: int) -> None:
    names = [f"P{i+1}" for i in range(player_count)]
    settings = {
        "minutes_per_turn": random.choice([2, 3, 5]),
        "show_live_leaderboard": random.choice([True, False]),
    }
    game_id = client.begin_game(names, settings=settings)
    ids = [p["id"] for p in client.http.get("/api/players").json()]
    roster_ids = ids[-player_count:]

    for r in range(1, rounds + 1):
        for p in range(player_count):
            points = 10 + r + p
            res = client.turn(game_id, points=points, play_type="score")
            if res.status_code != 200:
                record_issue(
                    run,
                    "Live play",
                    f"Valid turn rejected ({res.status_code})",
                    f"User {run.email}, game {game_id}: POST turns points={points} -> {res.text[:120]}",
                )
                return

    invalid = client.turn(game_id, points=0, play_type="score")
    if invalid.status_code != 400:
        record_issue(
            run,
            "Live play",
            "Invalid zero points accepted",
            f"User {run.email}, game {game_id}: POST turns points=0 expected 400, got {invalid.status_code}",
        )

    state = client.game_state(game_id)
    if settings["show_live_leaderboard"]:
        if any(s.get("total_score") is None for s in state.get("standings", [])):
            record_issue(
                run,
                "Live play",
                "Standings hidden when show_live_leaderboard is true",
                f"User {run.email}, game {game_id}: settings show_live_leaderboard=true but totals null",
            )

    result = client.end_and_finalize(game_id, roster_ids)
    if result.get("status") != "completed":
        record_issue(
            run,
            "End game",
            "Finalize did not complete game",
            f"User {run.email}, game {game_id}: finalize status={result.get('status')}",
        )

    detail = client.http.get(f"/api/games/{game_id}")
    if detail.status_code != 200:
        record_issue(
            run,
            "History",
            "Completed game detail unavailable",
            f"User {run.email}, game {game_id}: GET /api/games/{game_id} -> {detail.status_code}",
        )

    listing = client.http.get("/api/games", params={"status": "completed"})
    if not any(g["id"] == game_id for g in listing.json()):
        record_issue(
            run,
            "History",
            "Completed game missing from list",
            f"User {run.email}, game {game_id}: not in GET /api/games?status=completed",
        )

    board = client.http.get("/api/leaderboard")
    if board.status_code != 200:
        record_issue(
            run,
            "Leaderboard",
            "Leaderboard request failed",
            f"User {run.email}: GET /api/leaderboard -> {board.status_code}",
        )


def scenario_challenge_skip(client: QAClient, run: QARun) -> None:
    game_id = client.begin_game(["C1", "C2"])
    ch = client.turn(game_id, play_type="challenge")
    if ch.status_code != 200:
        record_issue(
            run,
            "Live play",
            "Challenge turn failed",
            f"User {run.email}, game {game_id}: POST challenge -> {ch.status_code} {ch.text[:120]}",
        )
        return
    sk = client.turn(game_id, play_type="skip")
    if sk.status_code != 200:
        record_issue(
            run,
            "Live play",
            "Skip turn failed",
            f"User {run.email}, game {game_id}: POST skip -> {sk.status_code} {sk.text[:120]}",
        )


def scenario_auth(client: QAClient, run: QARun, email: str) -> None:
    me = client.http.get("/auth/me")
    if me.status_code != 200:
        record_issue(
            run,
            "Auth",
            "Session not established after login",
            f"User {email}: GET /auth/me -> {me.status_code}",
        )
    logout = client.http.post("/auth/logout")
    if logout.status_code not in (200, 204):
        record_issue(
            run,
            "Auth",
            "Logout failed",
            f"User {email}: POST /auth/logout -> {logout.status_code}",
        )
    client.login(email)
    me2 = client.http.get("/auth/me")
    if me2.status_code != 200:
        record_issue(
            run,
            "Auth",
            "Re-login did not restore session",
            f"User {email}: login again then GET /auth/me -> {me2.status_code}",
        )


def run_batch(batch: int) -> QARun:
    email = f"qa+{int(time.time())}@test.local"
    print(f"\n=== QA batch {batch} — {email} ===")
    run = QARun(email=email)
    client = QAClient()
    try:
        client.register(email)
        scenario_auth(client, run, email)

        player_count = random.choice([2, 3, 4])
        rounds = random.choice([2, 3, 4])
        scenario_full_game(client, run, player_count, rounds)
        scenario_challenge_skip(client, run)

        if random.random() < 0.5:
            scenario_full_game(client, run, 2, 2)

        print(f"Batch {batch} complete — {len(run.issues)} issue(s) found")
    except Exception as exc:  # noqa: BLE001
        record_issue(
            run,
            "Agent",
            f"Batch crashed: {exc.__class__.__name__}",
            f"User {email}, batch {batch}: {exc}\n{traceback.format_exc()[-400:]}",
        )
        print(f"Batch {batch} error: {exc}", file=sys.stderr)
    finally:
        client.close()
    return run


def main() -> int:
    print(f"QA agent started — target {BASE_URL} (Ctrl+C to stop)")
    batch = 0
    try:
        while True:
            batch += 1
            run = run_batch(batch)
            append_readme_issues(run)
            print(f"Sleeping {LOOP_SLEEP_SEC}s before next batch...")
            time.sleep(LOOP_SLEEP_SEC)
    except KeyboardInterrupt:
        print("\nQA agent stopped.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
