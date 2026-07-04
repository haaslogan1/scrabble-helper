from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models import (
    FriendRequest,
    FriendRequestStatus,
    Friendship,
    Game,
    GamePlayer,
    GameStatus,
    NotificationType,
    Player,
    User,
)
from app import notifications as notification_service

USERNAME_RE = re.compile(r"^[a-z0-9_]{3,32}$")


def assign_default_username(db: Session, user: User) -> None:
    if user.username:
        return
    base = (user.email.split("@")[0] or "user").lower()
    base = "".join(ch for ch in base if ch.isalnum() or ch == "_")[:32] or "user"
    candidate = base
    suffix = 1
    while (
        db.query(User)
        .filter(User.username == candidate, User.id != user.id)
        .one_or_none()
    ):
        suffix += 1
        candidate = f"{base}{suffix}"[:32]
    user.username = candidate
    db.commit()
    db.refresh(user)


def validate_username(username: str) -> str:
    username = username.strip().lower()
    if not USERNAME_RE.match(username):
        raise HTTPException(
            status_code=400,
            detail="Username must be 3–32 characters: lowercase letters, numbers, and underscores only.",
        )
    return username


def user_display_label(user: User) -> str:
    if user.username:
        return f"@{user.username}"
    return user.name


def are_mutual_friends(db: Session, user_a_id: int, user_b_id: int) -> bool:
    if user_a_id == user_b_id:
        return True
    a_to_b = (
        db.query(Friendship)
        .filter(Friendship.user_id == user_a_id, Friendship.friend_user_id == user_b_id)
        .first()
    )
    b_to_a = (
        db.query(Friendship)
        .filter(Friendship.user_id == user_b_id, Friendship.friend_user_id == user_a_id)
        .first()
    )
    return a_to_b is not None and b_to_a is not None


def is_following(db: Session, user_id: int, friend_user_id: int) -> bool:
    return (
        db.query(Friendship)
        .filter(Friendship.user_id == user_id, Friendship.friend_user_id == friend_user_id)
        .first()
        is not None
    )


def _create_mutual_friendships(db: Session, user_a_id: int, user_b_id: int) -> None:
    for owner_id, friend_id in ((user_a_id, user_b_id), (user_b_id, user_a_id)):
        existing = (
            db.query(Friendship)
            .filter(Friendship.user_id == owner_id, Friendship.friend_user_id == friend_id)
            .one_or_none()
        )
        if existing is None:
            db.add(Friendship(user_id=owner_id, friend_user_id=friend_id))
    db.commit()
    ensure_friend_player(db, user_a_id, user_b_id)
    ensure_friend_player(db, user_b_id, user_a_id)


def ensure_friend_player(db: Session, owner_user_id: int, friend_user_id: int) -> Player:
    friend_user = db.get(User, friend_user_id)
    if friend_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    player = (
        db.query(Player)
        .filter(
            Player.owner_user_id == owner_user_id,
            Player.linked_user_id == friend_user_id,
        )
        .one_or_none()
    )
    if player:
        if player.name != friend_user.name:
            player.name = friend_user.name
            db.commit()
            db.refresh(player)
        return player

    player = Player(
        owner_user_id=owner_user_id,
        name=friend_user.name,
        linked_user_id=friend_user_id,
    )
    db.add(player)
    try:
        db.commit()
        db.refresh(player)
    except Exception:
        db.rollback()
        player = (
            db.query(Player)
            .filter(
                Player.owner_user_id == owner_user_id,
                Player.linked_user_id == friend_user_id,
            )
            .one()
        )
    return player


def list_friends(db: Session, user_id: int) -> list[dict[str, Any]]:
    rows = (
        db.query(Friendship, User)
        .join(User, User.id == Friendship.friend_user_id)
        .filter(Friendship.user_id == user_id)
        .order_by(User.name.asc())
        .all()
    )
    result = []
    for _friendship, friend in rows:
        if not are_mutual_friends(db, user_id, friend.id):
            continue
        result.append(
            {
                "id": friend.id,
                "username": friend.username,
                "name": friend.name,
                "mutual": True,
            }
        )
    return result


def list_incoming_requests(db: Session, user_id: int) -> list[dict[str, Any]]:
    rows = (
        db.query(FriendRequest, User)
        .join(User, User.id == FriendRequest.from_user_id)
        .filter(
            FriendRequest.to_user_id == user_id,
            FriendRequest.status == FriendRequestStatus.pending,
        )
        .order_by(FriendRequest.created_at.desc())
        .all()
    )
    return [
        {
            "id": req.id,
            "from_user": {
                "id": user.id,
                "username": user.username,
                "name": user.name,
            },
            "created_at": req.created_at.isoformat(),
        }
        for req, user in rows
    ]


def _resolve_target_user(
    db: Session, *, friend_user_id: int | None, username: str | None
) -> User:
    if friend_user_id is None and username is None:
        raise HTTPException(status_code=400, detail="user_id or username required")
    if friend_user_id is None:
        username = validate_username(username or "")
        friend = db.query(User).filter(User.username == username).one_or_none()
        if friend is None:
            raise HTTPException(status_code=404, detail="User not found")
        return friend
    friend = db.get(User, friend_user_id)
    if friend is None:
        raise HTTPException(status_code=404, detail="User not found")
    return friend


def send_friend_request(
    db: Session, user_id: int, *, friend_user_id: int | None = None, username: str | None = None
) -> dict[str, Any]:
    friend = _resolve_target_user(db, friend_user_id=friend_user_id, username=username)
    if friend.id == user_id:
        raise HTTPException(status_code=400, detail="Cannot add yourself as a friend")

    if are_mutual_friends(db, user_id, friend.id):
        raise HTTPException(status_code=400, detail="You are already friends")

    existing = (
        db.query(FriendRequest)
        .filter(
            FriendRequest.from_user_id == user_id,
            FriendRequest.to_user_id == friend.id,
        )
        .one_or_none()
    )
    if existing and existing.status == FriendRequestStatus.pending:
        raise HTTPException(status_code=400, detail="Friend request already sent")
    if existing and existing.status == FriendRequestStatus.declined:
        existing.status = FriendRequestStatus.pending
        existing.responded_at = None
        existing.created_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        request = existing
    elif existing is None:
        request = FriendRequest(from_user_id=user_id, to_user_id=friend.id)
        db.add(request)
        db.commit()
        db.refresh(request)
    else:
        raise HTTPException(status_code=400, detail="Friend request already accepted")

    reverse_pending = (
        db.query(FriendRequest)
        .filter(
            FriendRequest.from_user_id == friend.id,
            FriendRequest.to_user_id == user_id,
            FriendRequest.status == FriendRequestStatus.pending,
        )
        .one_or_none()
    )
    if reverse_pending:
        return accept_friend_request(db, user_id, reverse_pending.id)

    sender = db.get(User, user_id)
    notification_service.create_notification(
        db,
        friend.id,
        NotificationType.friend_request,
        title="Friend request",
        body=f"{sender.name if sender else 'Someone'} sent you a friend request",
        payload={
            "friend_request_id": request.id,
            "actor_user_id": user_id,
        },
    )
    return {
        "id": friend.id,
        "username": friend.username,
        "name": friend.name,
        "request_id": request.id,
        "status": "pending",
    }


def accept_friend_request(db: Session, user_id: int, request_id: int) -> dict[str, Any]:
    request = db.get(FriendRequest, request_id)
    if request is None or request.to_user_id != user_id:
        raise HTTPException(status_code=404, detail="Friend request not found")
    if request.status != FriendRequestStatus.pending:
        raise HTTPException(status_code=400, detail="Friend request is not pending")

    request.status = FriendRequestStatus.accepted
    request.responded_at = datetime.utcnow()
    db.commit()

    _create_mutual_friendships(db, request.from_user_id, request.to_user_id)

    accepter = db.get(User, user_id)
    requester = db.get(User, request.from_user_id)
    if requester and accepter:
        notification_service.create_notification(
            db,
            request.from_user_id,
            NotificationType.friend_request_accepted,
            title="Friend request accepted",
            body=f"{accepter.name} accepted your friend request",
            payload={"actor_user_id": user_id},
        )
        notification_service.create_notification(
            db,
            user_id,
            NotificationType.friend_mutual,
            title="New friend",
            body=f"You and {requester.name} are now friends",
            payload={"actor_user_id": request.from_user_id},
        )

    notification_service.dismiss_for_friend_request(db, user_id, request_id)

    friend = db.get(User, request.from_user_id)
    return {
        "id": friend.id if friend else request.from_user_id,
        "username": friend.username if friend else None,
        "name": friend.name if friend else "",
        "mutual": True,
    }


def decline_friend_request(db: Session, user_id: int, request_id: int) -> dict[str, str]:
    request = db.get(FriendRequest, request_id)
    if request is None or request.to_user_id != user_id:
        raise HTTPException(status_code=404, detail="Friend request not found")
    if request.status != FriendRequestStatus.pending:
        raise HTTPException(status_code=400, detail="Friend request is not pending")

    request.status = FriendRequestStatus.declined
    request.responded_at = datetime.utcnow()
    db.commit()

    decliner = db.get(User, user_id)
    if decliner:
        notification_service.create_notification(
            db,
            request.from_user_id,
            NotificationType.friend_request_declined,
            title="Friend request declined",
            body=f"{decliner.name} declined your friend request",
            payload={"actor_user_id": user_id},
        )

    notification_service.dismiss_for_friend_request(db, user_id, request_id)
    return {"status": "ok"}


def accept_friend_request_from_notification(
    db: Session, user_id: int, notification_id: int
) -> dict[str, Any]:
    notification = notification_service.get_notification(db, user_id, notification_id)
    if notification.type != NotificationType.friend_request:
        raise HTTPException(status_code=400, detail="Not a friend request notification")
    request_id = notification.payload.get("friend_request_id")
    if not request_id:
        raise HTTPException(status_code=400, detail="Invalid notification payload")
    return accept_friend_request(db, user_id, int(request_id))


def decline_friend_request_from_notification(
    db: Session, user_id: int, notification_id: int
) -> dict[str, str]:
    notification = notification_service.get_notification(db, user_id, notification_id)
    if notification.type != NotificationType.friend_request:
        raise HTTPException(status_code=400, detail="Not a friend request notification")
    request_id = notification.payload.get("friend_request_id")
    if not request_id:
        raise HTTPException(status_code=400, detail="Invalid notification payload")
    return decline_friend_request(db, user_id, int(request_id))


def add_friend(
    db: Session, user_id: int, *, friend_user_id: int | None = None, username: str | None = None
) -> dict[str, Any]:
    return send_friend_request(db, user_id, friend_user_id=friend_user_id, username=username)


def remove_friend(db: Session, user_id: int, friend_user_id: int) -> None:
    for owner_id, other_id in ((user_id, friend_user_id), (friend_user_id, user_id)):
        friendship = (
            db.query(Friendship)
            .filter(Friendship.user_id == owner_id, Friendship.friend_user_id == other_id)
            .one_or_none()
        )
        if friendship:
            db.delete(friendship)
        linked_player = (
            db.query(Player)
            .filter(
                Player.owner_user_id == owner_id,
                Player.linked_user_id == other_id,
            )
            .one_or_none()
        )
        if linked_player:
            from app.models import Game, GamePlayer, GameStatus

            draft_game_ids = (
                db.query(GamePlayer.game_id)
                .join(Game, Game.id == GamePlayer.game_id)
                .filter(
                    GamePlayer.player_id == linked_player.id,
                    Game.status == GameStatus.draft,
                )
                .all()
            )
            for (gid,) in draft_game_ids:
                db.query(GamePlayer).filter(
                    GamePlayer.game_id == gid,
                    GamePlayer.player_id == linked_player.id,
                ).delete(synchronize_session=False)
            db.delete(linked_player)
    db.commit()


def friend_suggestions(db: Session, user_id: int) -> list[dict[str, Any]]:
    mutual_ids = {
        row[0]
        for row in db.query(Friendship.friend_user_id)
        .filter(Friendship.user_id == user_id)
        .all()
        if are_mutual_friends(db, user_id, row[0])
    }
    mutual_ids.add(user_id)

    pending_from = {
        row[0]
        for row in db.query(FriendRequest.from_user_id)
        .filter(
            FriendRequest.to_user_id == user_id,
            FriendRequest.status == FriendRequestStatus.pending,
        )
        .all()
    }

    friends_of_friends: list[User] = []
    if mutual_ids:
        fof_ids = (
            db.query(Friendship.friend_user_id)
            .filter(
                Friendship.user_id.in_(mutual_ids - {user_id}),
                Friendship.friend_user_id.notin_(mutual_ids),
            )
            .distinct()
            .all()
        )
        if fof_ids:
            friends_of_friends = (
                db.query(User)
                .filter(User.id.in_([row[0] for row in fof_ids]))
                .order_by(User.name.asc())
                .limit(20)
                .all()
            )

    seen: set[int] = set()
    result: list[dict[str, Any]] = []
    for user in friends_of_friends:
        if user.id in seen or user.id in pending_from:
            continue
        seen.add(user.id)
        result.append(
            {
                "id": user.id,
                "username": user.username,
                "name": user.name,
                "reason": "friend_of_friend",
            }
        )
    return result


def search_users(db: Session, user_id: int, query: str) -> list[dict[str, Any]]:
    q = query.strip().lower()
    if not q:
        return []
    if q.startswith("@"):
        q = q[1:]

    filters = [User.username.ilike(f"{q}%")]
    if "@" in query.strip():
        filters.append(User.email == query.strip().lower())
    else:
        filters.append(User.email.ilike(f"{query.strip().lower()}%"))

    users = (
        db.query(User)
        .filter(or_(*filters), User.id != user_id)
        .order_by(User.username.asc().nullslast(), User.name.asc())
        .limit(25)
        .all()
    )
    return [{"id": u.id, "username": u.username, "name": u.name} for u in users]


def set_username(db: Session, user: User, username: str) -> User:
    username = validate_username(username)
    taken = (
        db.query(User)
        .filter(User.username == username, User.id != user.id)
        .one_or_none()
    )
    if taken:
        raise HTTPException(status_code=409, detail="Username already taken")
    user.username = username
    db.commit()
    db.refresh(user)
    return user


def user_in_active_live_game(
    db: Session, user_id: int, *, exclude_game_id: int | None = None
) -> Game | None:
    query = (
        db.query(Game)
        .join(GamePlayer, GamePlayer.game_id == Game.id)
        .join(Player, Player.id == GamePlayer.player_id)
        .filter(
            Player.linked_user_id == user_id,
            Game.status.in_([GameStatus.active, GameStatus.ending]),
        )
    )
    if exclude_game_id is not None:
        query = query.filter(Game.id != exclude_game_id)
    return query.first()


def validate_linked_players_for_live(
    db: Session,
    owner_user_id: int,
    players: list[Player],
    *,
    exclude_game_id: int | None = None,
) -> None:
    for player in players:
        if player.linked_user_id is None:
            continue
        friend = db.get(User, player.linked_user_id)
        if friend is None:
            continue
        if not are_mutual_friends(db, owner_user_id, player.linked_user_id):
            label = friend.name
            raise HTTPException(
                status_code=400,
                detail=f"{label} must add you as a friend before you can play a live game together.",
            )
        active = user_in_active_live_game(
            db, player.linked_user_id, exclude_game_id=exclude_game_id
        )
        if active:
            label = user_display_label(friend)
            raise HTTPException(
                status_code=400,
                detail=f"User {label} is already playing a live game.",
            )


def player_out_extra(db: Session, owner_user_id: int, player: Player) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": player.id,
        "name": player.name,
        "linked_user_id": player.linked_user_id,
        "is_friend": player.linked_user_id is not None,
        "mutual": None,
        "is_self": player.linked_user_id == owner_user_id,
    }
    if player.linked_user_id is not None:
        data["mutual"] = are_mutual_friends(db, owner_user_id, player.linked_user_id)
    return data


def notify_live_game_started(db: Session, game: Game) -> None:
    host = db.get(User, game.owner_user_id)
    if host is None:
        return
    for gp in game.game_players:
        linked_id = gp.player.linked_user_id
        if linked_id is None or linked_id == game.owner_user_id:
            continue
        if not are_mutual_friends(db, game.owner_user_id, linked_id):
            continue
        notification_service.create_notification(
            db,
            linked_id,
            NotificationType.live_game_started,
            title="Live game started",
            body=f"{host.name} started a live game with you",
            payload={"game_id": game.id, "actor_user_id": game.owner_user_id},
        )


def notify_game_completed(db: Session, game: Game) -> None:
    host = db.get(User, game.owner_user_id)
    if host is None:
        return
    for gp in game.game_players:
        linked_id = gp.player.linked_user_id
        if linked_id is None or linked_id == game.owner_user_id:
            continue
        if not are_mutual_friends(db, game.owner_user_id, linked_id):
            continue
        notification_service.create_notification(
            db,
            linked_id,
            NotificationType.game_completed,
            title="Game completed",
            body=f"{host.name} completed a game you played in",
            payload={"game_id": game.id, "actor_user_id": game.owner_user_id},
        )
