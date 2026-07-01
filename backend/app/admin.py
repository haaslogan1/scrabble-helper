from __future__ import annotations

from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from app import auth
from app.models import Game, User


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


def list_games(db: Session, owner_email: str | None = None) -> list[dict]:
    query = db.query(Game)
    if owner_email:
        owner = db.query(User).filter(User.email == owner_email.strip().lower()).one_or_none()
        if owner is None:
            return []
        query = query.filter(Game.owner_user_id == owner.id)
    games = query.order_by(Game.id.desc()).all()
    return [
        {
            "id": g.id,
            "owner_user_id": g.owner_user_id,
            "status": g.status.value,
            "played_date": g.played_date.isoformat() if g.played_date else None,
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
