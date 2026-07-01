"""User-scoped statistics queries."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Game, GamePlayer, GameStatus, PlayType, Player, Round


def _user_game_ids(db: Session, user_id: int) -> select:
    return select(Game.id).where(
        Game.owner_user_id == user_id,
        Game.status == GameStatus.completed,
    )


def win_leaderboard(db: Session, user_id: int) -> list[dict[str, Any]]:
    game_ids = _user_game_ids(db, user_id)
    rows = db.execute(
        select(Player.name, func.count())
        .join(GamePlayer, GamePlayer.player_id == Player.id)
        .where(GamePlayer.game_id.in_(game_ids), GamePlayer.won.is_(True))
        .group_by(Player.id)
        .order_by(func.count().desc(), Player.name.asc())
    ).all()
    return [{"player": name, "wins": count} for name, count in rows]


def total_points_all_time(db: Session, user_id: int) -> list[dict[str, Any]]:
    game_ids = _user_game_ids(db, user_id)
    rows = db.execute(
        select(Player.name, func.round(func.sum(GamePlayer.total_score), 2))
        .join(GamePlayer, GamePlayer.player_id == Player.id)
        .where(GamePlayer.game_id.in_(game_ids))
        .group_by(Player.id)
        .order_by(func.sum(GamePlayer.total_score).desc(), Player.name.asc())
    ).all()
    return [{"player": name, "total_points": float(total)} for name, total in rows]


def avg_points_per_play(db: Session, user_id: int) -> list[dict[str, Any]]:
    game_ids = _user_game_ids(db, user_id)
    rows = db.execute(
        select(
            Player.name,
            func.round(func.sum(Round.score) * 1.0 / func.count(Round.id), 2),
        )
        .join(Round, Round.player_id == Player.id)
        .where(Round.game_id.in_(game_ids), Round.score != 0)
        .group_by(Player.id)
        .order_by((func.sum(Round.score) / func.count(Round.id)).desc(), Player.name.asc())
    ).all()
    return [{"player": name, "avg_per_play": float(avg)} for name, avg in rows]


def avg_total_points_per_game(db: Session, user_id: int) -> list[dict[str, Any]]:
    game_ids = _user_game_ids(db, user_id)
    rows = db.execute(
        select(Player.name, func.round(func.avg(GamePlayer.total_score), 2))
        .join(GamePlayer, GamePlayer.player_id == Player.id)
        .where(GamePlayer.game_id.in_(game_ids))
        .group_by(Player.id)
        .order_by(func.avg(GamePlayer.total_score).desc(), Player.name.asc())
    ).all()
    return [{"player": name, "avg_total": float(avg)} for name, avg in rows]


def lost_challenges_or_skipped_turns(db: Session, user_id: int) -> list[dict[str, Any]]:
    game_ids = _user_game_ids(db, user_id)
    rows = db.execute(
        select(Player.name, func.count())
        .join(Round, Round.player_id == Player.id)
        .where(
            Round.game_id.in_(game_ids),
            Round.play_type.in_([PlayType.challenge, PlayType.skip]),
        )
        .group_by(Player.id)
        .order_by(func.count().desc(), Player.name.asc())
    ).all()
    return [{"player": name, "count": count} for name, count in rows]


def games_played(db: Session, user_id: int) -> list[dict[str, Any]]:
    game_ids = _user_game_ids(db, user_id)
    rows = db.execute(
        select(Player.name, func.count(func.distinct(GamePlayer.game_id)))
        .join(GamePlayer, GamePlayer.player_id == Player.id)
        .where(GamePlayer.game_id.in_(game_ids))
        .group_by(Player.id)
        .order_by(func.count(func.distinct(GamePlayer.game_id)).desc(), Player.name.asc())
    ).all()
    return [{"player": name, "games_played": count} for name, count in rows]


def all_stats(db: Session, user_id: int) -> dict[str, list[dict[str, Any]]]:
    return {
        "win_leaderboard": win_leaderboard(db, user_id),
        "total_points": total_points_all_time(db, user_id),
        "avg_points_per_play": avg_points_per_play(db, user_id),
        "avg_total_per_game": avg_total_points_per_game(db, user_id),
        "lost_challenges_or_skipped_turns": lost_challenges_or_skipped_turns(db, user_id),
        "games_played": games_played(db, user_id),
    }
