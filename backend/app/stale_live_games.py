"""Stale live-game sweep and recovery helpers."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Callable

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.models import Game, GamePlayer, GameStatus, Player, User

GetGameAccess = Callable[[Session, int, int], tuple[Game, str]]
LoadGame = Callable[[Session, int], Game | None]


def inactivity_warn_after_sec() -> int:
    return settings.inactivity_warn_after_sec


def inactivity_end_after_sec() -> int:
    return settings.inactivity_auto_end_after_sec


def idle_seconds(game: Game) -> float:
    if game.status == GameStatus.ending:
        anchor = game.ending_at or game.last_activity_at
    else:
        anchor = game.last_activity_at
    if not anchor:
        return 0.0
    return (datetime.utcnow() - anchor).total_seconds()


def zero_rack_adjustments(game: Game) -> dict[int, float]:
    return {gp.player_id: 0.0 for gp in game.game_players}


def _apply_finalize(db: Session, game: Game, rack_adjustments: dict) -> Game:
    from app.services import _apply_finalize as apply_finalize

    return apply_finalize(db, game, rack_adjustments)


def sweep_game_if_stale(db: Session, game: Game) -> bool:
    if game.status == GameStatus.active:
        if not game.last_activity_at or idle_seconds(game) < inactivity_end_after_sec():
            return False
        game.status = GameStatus.ending
        game.ending_at = datetime.utcnow()
        _apply_finalize(db, game, zero_rack_adjustments(game))
        return True
    if game.status == GameStatus.ending:
        if idle_seconds(game) < inactivity_end_after_sec():
            return False
        _apply_finalize(db, game, zero_rack_adjustments(game))
        return True
    return False


def games_for_linked_user(
    db: Session, user_id: int, *, statuses: list[GameStatus] | None = None
) -> list[Game]:
    statuses = statuses or [GameStatus.active, GameStatus.ending]
    return (
        db.query(Game)
        .options(joinedload(Game.game_players).joinedload(GamePlayer.player))
        .join(GamePlayer, GamePlayer.game_id == Game.id)
        .join(Player, Player.id == GamePlayer.player_id)
        .filter(
            Player.linked_user_id == user_id,
            Game.status.in_(statuses),
        )
        .all()
    )


def sweep_games_for_user(db: Session, user_id: int) -> int:
    count = 0
    for game in games_for_linked_user(db, user_id):
        if sweep_game_if_stale(db, game):
            count += 1
    return count


def sweep_stale_live_games(db: Session, *, limit: int = 50) -> int:
    cutoff = datetime.utcnow() - timedelta(seconds=inactivity_end_after_sec())
    active_games = (
        db.query(Game)
        .options(joinedload(Game.game_players).joinedload(GamePlayer.player))
        .filter(
            Game.status == GameStatus.active,
            Game.last_activity_at.isnot(None),
            Game.last_activity_at < cutoff,
        )
        .order_by(Game.last_activity_at.asc())
        .limit(limit)
        .all()
    )
    ending_games = (
        db.query(Game)
        .options(joinedload(Game.game_players).joinedload(GamePlayer.player))
        .filter(Game.status == GameStatus.ending)
        .order_by(Game.ending_at.asc().nullslast(), Game.last_activity_at.asc())
        .limit(limit)
        .all()
    )
    count = 0
    for game in active_games + ending_games:
        if count >= limit:
            break
        if sweep_game_if_stale(db, game):
            count += 1
    return count


def participant_can_abandon(game: Game) -> bool:
    return game.status in (GameStatus.active, GameStatus.ending) and (
        idle_seconds(game) >= inactivity_end_after_sec()
    )


def list_participating_games(
    db: Session,
    user_id: int,
    *,
    statuses: list[GameStatus] | None = None,
) -> list[dict[str, Any]]:
    sweep_games_for_user(db, user_id)
    statuses = statuses or [GameStatus.active, GameStatus.ending]
    games = (
        db.query(Game)
        .options(joinedload(Game.game_players).joinedload(GamePlayer.player))
        .join(GamePlayer, GamePlayer.game_id == Game.id)
        .join(Player, Player.id == GamePlayer.player_id)
        .filter(
            Player.linked_user_id == user_id,
            Game.owner_user_id != user_id,
            Game.status.in_(statuses),
        )
        .order_by(Game.last_activity_at.desc().nullslast(), Game.id.desc())
        .all()
    )
    result = []
    for game in games:
        owner = db.get(User, game.owner_user_id)
        result.append(
            {
                "id": game.id,
                "status": game.status.value,
                "role": "participant",
                "owner_name": owner.name if owner else "Unknown",
                "last_activity_at": (
                    game.last_activity_at.isoformat() if game.last_activity_at else None
                ),
                "can_finalize": False,
                "can_abandon": participant_can_abandon(game),
                "resume_url": f"/game/{game.id}/play",
            }
        )
    return result


def abandon_game(
    db: Session,
    user_id: int,
    game_id: int,
    *,
    get_game_access: GetGameAccess,
    load_game: LoadGame,
) -> Game:
    game, role = get_game_access(db, user_id, game_id)
    if game.status in (GameStatus.draft, GameStatus.completed):
        raise HTTPException(status_code=400, detail="Game cannot be abandoned")
    if role == "spectator" and not participant_can_abandon(game):
        raise HTTPException(
            status_code=403,
            detail="Only the owner can end an active game before it times out",
        )
    if role not in ("owner", "spectator"):
        raise HTTPException(status_code=403, detail="Not allowed")
    if game.status == GameStatus.active:
        game.status = GameStatus.ending
        game.ending_at = datetime.utcnow()
    _apply_finalize(db, game, zero_rack_adjustments(game))
    refreshed = load_game(db, game_id)
    if refreshed is None:
        raise HTTPException(status_code=404, detail="Game not found")
    return refreshed


def force_complete_game(db: Session, game_id: int, *, load_game: LoadGame) -> Game:
    game = load_game(db, game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")
    if game.status not in (GameStatus.active, GameStatus.ending):
        raise HTTPException(status_code=400, detail="Game is not in progress")
    if game.status == GameStatus.active:
        game.status = GameStatus.ending
        game.ending_at = datetime.utcnow()
    _apply_finalize(db, game, zero_rack_adjustments(game))
    refreshed = load_game(db, game_id)
    if refreshed is None:
        raise HTTPException(status_code=404, detail="Game not found")
    return refreshed
