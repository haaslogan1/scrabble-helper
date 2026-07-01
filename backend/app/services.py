from __future__ import annotations

from datetime import date, datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.models import Game, GamePlayer, GameStatus, PlayType, Player, Round
from app.scoring import PlayerScore, assign_placements, score_from_word, validate_turn_points


DEFAULT_SETTINGS: dict[str, Any] = {
    "minutes_per_turn": 3,
    "input_mode": "points",
    "show_live_leaderboard": True,
}


def list_players(db: Session, user_id: int) -> list[Player]:
    return (
        db.query(Player)
        .filter(Player.owner_user_id == user_id)
        .order_by(Player.name.asc())
        .all()
    )


def create_player(db: Session, user_id: int, name: str) -> Player:
    name = name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Player name required")
    existing = (
        db.query(Player)
        .filter(Player.owner_user_id == user_id, Player.name == name)
        .one_or_none()
    )
    if existing:
        return existing
    player = Player(owner_user_id=user_id, name=name)
    db.add(player)
    db.commit()
    db.refresh(player)
    return player


def get_owned_game(db: Session, user_id: int, game_id: int) -> Game:
    game = (
        db.query(Game)
        .options(joinedload(Game.game_players).joinedload(GamePlayer.player))
        .filter(Game.id == game_id, Game.owner_user_id == user_id)
        .one_or_none()
    )
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")
    return game


def create_game(db: Session, user_id: int, settings: dict[str, Any] | None = None) -> Game:
    merged = {**DEFAULT_SETTINGS, **(settings or {})}
    game = Game(owner_user_id=user_id, settings=merged, status=GameStatus.draft)
    db.add(game)
    db.commit()
    db.refresh(game)
    return game


def set_game_players(db: Session, user_id: int, game_id: int, player_ids: list[int]) -> Game:
    game = get_owned_game(db, user_id, game_id)
    if game.status != GameStatus.draft:
        raise HTTPException(status_code=400, detail="Game is not in draft status")
    if len(player_ids) < 2:
        raise HTTPException(status_code=400, detail="At least two players required")

    players = (
        db.query(Player)
        .filter(Player.owner_user_id == user_id, Player.id.in_(player_ids))
        .all()
    )
    if len(players) != len(player_ids):
        raise HTTPException(status_code=400, detail="Invalid player selection")

    db.query(GamePlayer).filter(GamePlayer.game_id == game.id).delete()
    for idx, player_id in enumerate(player_ids):
        db.add(
            GamePlayer(game_id=game.id, player_id=player_id, turn_order=idx)
        )
    db.commit()
    db.refresh(game)
    return game


def set_turn_order(db: Session, user_id: int, game_id: int, player_ids: list[int]) -> Game:
    game = get_owned_game(db, user_id, game_id)
    if game.status != GameStatus.draft:
        raise HTTPException(status_code=400, detail="Game is not in draft status")
    current_ids = {gp.player_id for gp in game.game_players}
    if set(player_ids) != current_ids:
        raise HTTPException(status_code=400, detail="Turn order must include same players")

    order_map = {pid: idx for idx, pid in enumerate(player_ids)}
    for gp in game.game_players:
        gp.turn_order = order_map[gp.player_id]
    db.commit()
    db.refresh(game)
    return game


def random_first_player(db: Session, user_id: int, game_id: int) -> Game:
    import random

    game = get_owned_game(db, user_id, game_id)
    if not game.game_players:
        raise HTTPException(status_code=400, detail="No players on game")
    ordered = sorted(game.game_players, key=lambda gp: gp.turn_order)
    first_idx = random.randrange(len(ordered))
    rotated = ordered[first_idx:] + ordered[:first_idx]
    for idx, gp in enumerate(rotated):
        gp.turn_order = idx
    db.commit()
    db.refresh(game)
    return game


def begin_game(db: Session, user_id: int, game_id: int) -> Game:
    game = get_owned_game(db, user_id, game_id)
    if game.status != GameStatus.draft:
        raise HTTPException(status_code=400, detail="Game is not in draft status")
    if len(game.game_players) < 2:
        raise HTTPException(status_code=400, detail="At least two players required")
    game.status = GameStatus.active
    game.started_at = datetime.utcnow()
    game.played_date = date.today()
    game.current_round = 1
    game.current_turn_index = 0
    db.commit()
    db.refresh(game)
    return game


def _ordered_players(game: Game) -> list[GamePlayer]:
    return sorted(game.game_players, key=lambda gp: gp.turn_order)


def _recompute_totals(db: Session, game: Game) -> None:
    db.flush()
    totals: dict[int, float] = {gp.player_id: 0.0 for gp in game.game_players}
    rounds = db.query(Round).filter(Round.game_id == game.id).all()
    for rnd in rounds:
        totals[rnd.player_id] = totals.get(rnd.player_id, 0.0) + rnd.score
    for gp in game.game_players:
        gp.total_score = totals.get(gp.player_id, 0.0) + gp.rack_adjustment


def _advance_turn_inplace(game: Game, ordered: list[GamePlayer]) -> None:
    if game.current_turn_index + 1 >= len(ordered):
        game.current_turn_index = 0
        game.current_round += 1
    else:
        game.current_turn_index += 1


def record_turn(
    db: Session,
    user_id: int,
    game_id: int,
    *,
    points: float | None = None,
    word: str | None = None,
    play_type: str = "score",
    timer_elapsed_sec: int | None = None,
) -> Game:
    game = get_owned_game(db, user_id, game_id)
    if game.status != GameStatus.active:
        raise HTTPException(status_code=400, detail="Game is not active")

    ordered = _ordered_players(game)
    current_gp = ordered[game.current_turn_index]
    input_mode = game.settings.get("input_mode", "points")
    ptype = PlayType(play_type)

    if ptype == PlayType.score:
        if input_mode == "words":
            if not word:
                raise HTTPException(status_code=400, detail="Word required in word mode")
            score = score_from_word(word)
        else:
            try:
                score = float(validate_turn_points(points))
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
    else:
        score = 0.0
        word = word or play_type

    existing = (
        db.query(Round)
        .filter(
            Round.game_id == game.id,
            Round.player_id == current_gp.player_id,
            Round.round_number == game.current_round,
        )
        .first()
    )
    if existing:
        existing.score = score
        existing.play_type = ptype
        existing.word = word
        existing.timer_elapsed_sec = timer_elapsed_sec
    else:
        db.add(
            Round(
                game_id=game.id,
                player_id=current_gp.player_id,
                round_number=game.current_round,
                score=score,
                play_type=ptype,
                word=word,
                timer_elapsed_sec=timer_elapsed_sec,
            )
        )
    _recompute_totals(db, game)
    _advance_turn_inplace(game, ordered)
    db.commit()
    db.refresh(game)
    return game


def advance_turn(db: Session, user_id: int, game_id: int) -> Game:
    game = get_owned_game(db, user_id, game_id)
    if game.status != GameStatus.active:
        raise HTTPException(status_code=400, detail="Game is not active")

    ordered = _ordered_players(game)
    _advance_turn_inplace(game, ordered)
    db.commit()
    db.refresh(game)
    return game


def end_game(db: Session, user_id: int, game_id: int) -> Game:
    game = get_owned_game(db, user_id, game_id)
    if game.status != GameStatus.active:
        raise HTTPException(status_code=400, detail="Game is not active")
    game.status = GameStatus.ending
    db.commit()
    db.refresh(game)
    return game


def finalize_game(
    db: Session,
    user_id: int,
    game_id: int,
    rack_adjustments: dict[str, float],
) -> Game:
    game = get_owned_game(db, user_id, game_id)
    if game.status != GameStatus.ending:
        raise HTTPException(status_code=400, detail="Game is not in ending status")

    for gp in game.game_players:
        adj = rack_adjustments.get(gp.player_id)
        if adj is None:
            adj = rack_adjustments.get(str(gp.player_id))
        if adj is not None:
            gp.rack_adjustment = float(adj)

    _recompute_totals(db, game)

    scores = [
        PlayerScore(
            player_id=gp.player_id,
            name=gp.player.name,
            total_score=gp.total_score,
            rack_adjustment=gp.rack_adjustment,
        )
        for gp in game.game_players
    ]
    assign_placements(scores)
    placement_map = {s.player_id: s for s in scores}
    for gp in game.game_players:
        scored = placement_map[gp.player_id]
        gp.placement = scored.placement
        gp.won = scored.won
        gp.total_score = scored.total_score

    game.status = GameStatus.completed
    game.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(game)
    return game


def list_games(
    db: Session, user_id: int, status: GameStatus | None = None
) -> list[Game]:
    query = db.query(Game).filter(Game.owner_user_id == user_id)
    if status:
        query = query.filter(Game.status == status)
    return query.order_by(Game.completed_at.desc().nullslast(), Game.id.desc()).all()


def game_state(db: Session, user_id: int, game_id: int) -> dict[str, Any]:
    game = get_owned_game(db, user_id, game_id)
    ordered = _ordered_players(game)
    show_board = game.settings.get("show_live_leaderboard", True)

    standings = []
    for gp in ordered:
        entry = {
            "player_id": gp.player_id,
            "name": gp.player.name,
            "total_score": gp.total_score if show_board or game.status != GameStatus.active else None,
            "turn_order": gp.turn_order,
        }
        standings.append(entry)

    current_player = None
    if game.status == GameStatus.active and ordered:
        current_player = ordered[game.current_turn_index].player.name

    return {
        "id": game.id,
        "status": game.status.value,
        "settings": game.settings,
        "current_round": game.current_round,
        "current_turn_index": game.current_turn_index,
        "current_player": current_player,
        "standings": standings,
        "started_at": game.started_at.isoformat() if game.started_at else None,
        "completed_at": game.completed_at.isoformat() if game.completed_at else None,
        "played_date": game.played_date.isoformat() if game.played_date else None,
    }


def game_detail(db: Session, user_id: int, game_id: int) -> dict[str, Any]:
    game = get_owned_game(db, user_id, game_id)
    ordered = _ordered_players(game)
    winner = next((gp for gp in ordered if gp.won), None)
    rounds = (
        db.query(Round)
        .filter(Round.game_id == game.id)
        .order_by(Round.round_number.asc(), Round.id.asc())
        .all()
    )
    return {
        **game_state(db, user_id, game_id),
        "winner": winner.player.name if winner else None,
        "players": [
            {
                "player_id": gp.player_id,
                "name": gp.player.name,
                "total_score": gp.total_score,
                "placement": gp.placement,
                "won": gp.won,
                "rack_adjustment": gp.rack_adjustment,
            }
            for gp in ordered
        ],
        "rounds": [
            {
                "round_number": r.round_number,
                "player_id": r.player_id,
                "score": r.score,
                "play_type": r.play_type.value,
                "word": r.word,
                "timer_elapsed_sec": r.timer_elapsed_sec,
            }
            for r in rounds
        ],
    }


def home_summary(db: Session, user_id: int) -> dict[str, Any]:
    completed = (
        db.query(Game)
        .filter(Game.owner_user_id == user_id, Game.status == GameStatus.completed)
        .count()
    )
    active = (
        db.query(Game)
        .filter(
            Game.owner_user_id == user_id,
            Game.status.in_([GameStatus.draft, GameStatus.active, GameStatus.ending]),
        )
        .count()
    )
    players = db.query(Player).filter(Player.owner_user_id == user_id).count()
    return {
        "completed_games": completed,
        "in_progress_games": active,
        "saved_players": players,
    }
