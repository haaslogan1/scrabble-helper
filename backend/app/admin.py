from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import services
from app.models import FeedbackSubmission, Game, GamePlayer, GameStatus, Player, User


def list_users(db: Session) -> list[dict]:
    users = db.query(User).order_by(User.id).all()
    result = []
    for user in users:
        game_count = db.query(Game).filter(Game.owner_user_id == user.id).count()
        result.append(
            {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "provider": user.provider,
                "is_admin": user.is_admin,
                "game_count": game_count,
            }
        )
    return result


def list_games(
    db: Session,
    owner_email: str | None = None,
    participant_email: str | None = None,
    statuses: list[GameStatus] | None = None,
) -> list[dict]:
    query = db.query(Game)
    if owner_email:
        owner = db.query(User).filter(User.email == owner_email.strip().lower()).one_or_none()
        if owner is None:
            return []
        query = query.filter(Game.owner_user_id == owner.id)
    if participant_email:
        participant = (
            db.query(User).filter(User.email == participant_email.strip().lower()).one_or_none()
        )
        if participant is None:
            return []
        query = (
            query.join(GamePlayer, GamePlayer.game_id == Game.id)
            .join(Player, Player.id == GamePlayer.player_id)
            .filter(Player.linked_user_id == participant.id)
        )
    if statuses:
        query = query.filter(Game.status.in_(statuses))
    games = query.order_by(Game.id.desc()).all()
    return [
        {
            "id": g.id,
            "owner_user_id": g.owner_user_id,
            "status": g.status.value,
            "played_date": g.played_date.isoformat() if g.played_date else None,
            "last_activity_at": g.last_activity_at.isoformat() if g.last_activity_at else None,
        }
        for g in games
    ]


def delete_game(db: Session, game_id: int) -> int:
    game = db.get(Game, game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")
    db.delete(game)
    db.commit()
    return game_id


def delete_all_games_for_user(db: Session, user_id: int) -> int:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    games = db.query(Game).filter(Game.owner_user_id == user_id).all()
    count = len(games)
    for game in games:
        db.delete(game)
    db.commit()
    return count


def delete_all_games_for_email(db: Session, email: str) -> int:
    user = db.query(User).filter(User.email == email.strip().lower()).one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return delete_all_games_for_user(db, user.id)


def force_complete_game(db: Session, game_id: int) -> dict:
    game = services.force_complete_game(db, game_id)
    return {"id": game.id, "status": game.status.value}


def sweep_stale_games(db: Session, *, limit: int = 50) -> dict:
    swept = services.sweep_stale_live_games(db, limit=limit)
    return {"swept": swept}


def list_feedback(db: Session, *, reviewed: bool | None = None) -> list[dict]:
    query = db.query(FeedbackSubmission).join(User, FeedbackSubmission.user_id == User.id)
    if reviewed is not None:
        query = query.filter(FeedbackSubmission.reviewed == reviewed)
    rows = query.order_by(FeedbackSubmission.created_at.desc()).all()
    result = []
    for row in rows:
        user = db.get(User, row.user_id)
        result.append(
            {
                "id": row.id,
                "user_email": user.email if user else "",
                "category": row.category,
                "message": row.message,
                "page_url": row.page_url,
                "game_id": row.game_id,
                "reviewed": row.reviewed,
                "created_at": row.created_at.isoformat(),
            }
        )
    return result


def update_feedback_reviewed(db: Session, feedback_id: int, reviewed: bool) -> dict:
    row = db.get(FeedbackSubmission, feedback_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Feedback not found")
    row.reviewed = reviewed
    db.commit()
    db.refresh(row)
    user = db.get(User, row.user_id)
    return {
        "id": row.id,
        "user_email": user.email if user else "",
        "category": row.category,
        "message": row.message,
        "page_url": row.page_url,
        "game_id": row.game_id,
        "reviewed": row.reviewed,
        "created_at": row.created_at.isoformat(),
    }
