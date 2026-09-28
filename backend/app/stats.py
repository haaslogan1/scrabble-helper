"""User-scoped statistics queries."""

from __future__ import annotations

from typing import Any, Literal

from sqlalchemy import Numeric, cast, func, select
from sqlalchemy.orm import Session

from app.models import GamePlayer, PlayType, Player, Round, User
from app.services import visible_completed_game_ids

LeaderboardScope = Literal["all", "friends", "manual"]


def _round2(expr):
    """PostgreSQL only implements round(numeric, digits), not round(float, digits)."""
    return func.round(cast(expr, Numeric), 2)


def _player_key():
    """Linked accounts are one entry across owners; manual players stay per-owner."""
    return func.coalesce(Player.linked_user_id, -Player.id)


def _player_name():
    return func.coalesce(User.name, Player.name)


def _player_select(*aggregates):
    return select(_player_name(), *aggregates).select_from(Player).outerjoin(
        User, User.id == Player.linked_user_id
    )


def _player_group():
    return (_player_key(), _player_name())


def _player_scope_clause(scope: LeaderboardScope):
    if scope == "friends":
        return [Player.linked_user_id.isnot(None)]
    if scope == "manual":
        return [Player.linked_user_id.is_(None)]
    return []


def win_leaderboard(
    db: Session, user_id: int, scope: LeaderboardScope = "all"
) -> list[dict[str, Any]]:
    game_ids = visible_completed_game_ids(user_id)
    rows = db.execute(
        _player_select(func.count())
        .join(GamePlayer, GamePlayer.player_id == Player.id)
        .where(
            GamePlayer.game_id.in_(game_ids),
            GamePlayer.won.is_(True),
            *_player_scope_clause(scope),
        )
        .group_by(*_player_group())
        .order_by(func.count().desc(), _player_name().asc())
    ).all()
    return [{"player": name, "wins": count} for name, count in rows]


def total_points_all_time(
    db: Session, user_id: int, scope: LeaderboardScope = "all"
) -> list[dict[str, Any]]:
    game_ids = visible_completed_game_ids(user_id)
    rows = db.execute(
        _player_select(_round2(func.sum(GamePlayer.total_score)))
        .join(GamePlayer, GamePlayer.player_id == Player.id)
        .where(GamePlayer.game_id.in_(game_ids), *_player_scope_clause(scope))
        .group_by(*_player_group())
        .order_by(func.sum(GamePlayer.total_score).desc(), _player_name().asc())
    ).all()
    return [{"player": name, "total_points": float(total)} for name, total in rows]


def avg_points_per_play(
    db: Session, user_id: int, scope: LeaderboardScope = "all"
) -> list[dict[str, Any]]:
    game_ids = visible_completed_game_ids(user_id)
    rows = db.execute(
        _player_select(_round2(func.sum(Round.score) * 1.0 / func.count(Round.id)))
        .join(Round, Round.player_id == Player.id)
        .where(
            Round.game_id.in_(game_ids),
            Round.score != 0,
            *_player_scope_clause(scope),
        )
        .group_by(*_player_group())
        .order_by((func.sum(Round.score) / func.count(Round.id)).desc(), _player_name().asc())
    ).all()
    return [{"player": name, "avg_per_play": float(avg)} for name, avg in rows]


def avg_total_points_per_game(
    db: Session, user_id: int, scope: LeaderboardScope = "all"
) -> list[dict[str, Any]]:
    game_ids = visible_completed_game_ids(user_id)
    rows = db.execute(
        _player_select(_round2(func.avg(GamePlayer.total_score)))
        .join(GamePlayer, GamePlayer.player_id == Player.id)
        .where(GamePlayer.game_id.in_(game_ids), *_player_scope_clause(scope))
        .group_by(*_player_group())
        .order_by(func.avg(GamePlayer.total_score).desc(), _player_name().asc())
    ).all()
    return [{"player": name, "avg_total": float(avg)} for name, avg in rows]


def lost_challenges_or_skipped_turns(
    db: Session, user_id: int, scope: LeaderboardScope = "all"
) -> list[dict[str, Any]]:
    game_ids = visible_completed_game_ids(user_id)
    rows = db.execute(
        _player_select(func.count())
        .join(Round, Round.player_id == Player.id)
        .where(
            Round.game_id.in_(game_ids),
            Round.play_type.in_([PlayType.challenge, PlayType.skip]),
            *_player_scope_clause(scope),
        )
        .group_by(*_player_group())
        .order_by(func.count().desc(), _player_name().asc())
    ).all()
    return [{"player": name, "count": count} for name, count in rows]


def games_played(
    db: Session, user_id: int, scope: LeaderboardScope = "all"
) -> list[dict[str, Any]]:
    game_ids = visible_completed_game_ids(user_id)
    rows = db.execute(
        _player_select(func.count(func.distinct(GamePlayer.game_id)))
        .join(GamePlayer, GamePlayer.player_id == Player.id)
        .where(GamePlayer.game_id.in_(game_ids), *_player_scope_clause(scope))
        .group_by(*_player_group())
        .order_by(func.count(func.distinct(GamePlayer.game_id)).desc(), _player_name().asc())
    ).all()
    return [{"player": name, "games_played": count} for name, count in rows]


def all_stats(
    db: Session, user_id: int, scope: LeaderboardScope = "all"
) -> dict[str, list[dict[str, Any]]]:
    return {
        "win_leaderboard": win_leaderboard(db, user_id, scope),
        "total_points": total_points_all_time(db, user_id, scope),
        "avg_points_per_play": avg_points_per_play(db, user_id, scope),
        "avg_total_per_game": avg_total_points_per_game(db, user_id, scope),
        "lost_challenges_or_skipped_turns": lost_challenges_or_skipped_turns(db, user_id, scope),
        "games_played": games_played(db, user_id, scope),
    }
