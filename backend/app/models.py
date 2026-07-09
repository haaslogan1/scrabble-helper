from __future__ import annotations

import enum
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class GameStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    ending = "ending"
    completed = "completed"


class PlayType(str, enum.Enum):
    score = "score"
    challenge = "challenge"
    skip = "skip"


class FriendRequestStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    declined = "declined"


class NotificationType(str, enum.Enum):
    friend_request = "friend_request"
    friend_request_accepted = "friend_request_accepted"
    friend_request_declined = "friend_request_declined"
    friend_mutual = "friend_mutual"
    live_game_started = "live_game_started"
    game_completed = "game_completed"


class PhotoContext(str, enum.Enum):
    board = "board"
    group = "group"
    other = "other"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(32), unique=True, nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False, default="google")
    provider_sub: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    totp_secret: Mapped[str | None] = mapped_column(String(255), nullable=True)
    google_avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    avatar_storage_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    session_version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_session_user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    players: Mapped[list["Player"]] = relationship(
        back_populates="owner",
        foreign_keys="[Player.owner_user_id]",
    )
    games: Mapped[list[Game]] = relationship(back_populates="owner")

    __table_args__ = (UniqueConstraint("provider", "provider_sub"),)


class Friendship(Base):
    __tablename__ = "friendships"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    friend_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    __table_args__ = (UniqueConstraint("user_id", "friend_user_id"),)


class FriendRequest(Base):
    __tablename__ = "friend_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    from_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    to_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    status: Mapped[FriendRequestStatus] = mapped_column(
        Enum(FriendRequestStatus), default=FriendRequestStatus.pending, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    responded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    from_user: Mapped[User] = relationship(foreign_keys=[from_user_id])
    to_user: Mapped[User] = relationship(foreign_keys=[to_user_id])

    __table_args__ = (UniqueConstraint("from_user_id", "to_user_id"),)


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    type: Mapped[NotificationType] = mapped_column(Enum(NotificationType), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(String(512), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    user: Mapped[User] = relationship(foreign_keys=[user_id])


class EmailVerification(Base):
    __tablename__ = "email_verifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )


class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    linked_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    owner: Mapped[User] = relationship(back_populates="players", foreign_keys=[owner_user_id])
    linked_user: Mapped[User | None] = relationship(foreign_keys=[linked_user_id])

    __table_args__ = (
        UniqueConstraint("owner_user_id", "name"),
        UniqueConstraint("owner_user_id", "linked_user_id"),
    )


class Game(Base):
    __tablename__ = "games"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    status: Mapped[GameStatus] = mapped_column(
        Enum(GameStatus), default=GameStatus.draft, nullable=False
    )
    settings: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    played_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ending_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    current_round: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    current_turn_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    owner: Mapped[User] = relationship(back_populates="games")
    game_players: Mapped[list[GamePlayer]] = relationship(
        back_populates="game", cascade="all, delete-orphan"
    )
    rounds: Mapped[list[Round]] = relationship(
        back_populates="game", cascade="all, delete-orphan"
    )


class GamePlayer(Base):
    __tablename__ = "game_players"

    game_id: Mapped[int] = mapped_column(ForeignKey("games.id"), primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), primary_key=True)
    turn_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    placement: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    won: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    rack_adjustment: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    game: Mapped[Game] = relationship(back_populates="game_players")
    player: Mapped[Player] = relationship()


class FeedbackSubmission(Base):
    __tablename__ = "feedback_submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    page_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    game_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reviewed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    user: Mapped[User] = relationship(foreign_keys=[user_id])


class Round(Base):
    __tablename__ = "rounds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id"), nullable=False)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False)
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    play_type: Mapped[PlayType] = mapped_column(
        Enum(PlayType), default=PlayType.score, nullable=False
    )
    word: Mapped[str | None] = mapped_column(Text, nullable=True)
    timer_elapsed_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)

    game: Mapped[Game] = relationship(back_populates="rounds")
    player: Mapped[Player] = relationship()

    __table_args__ = (
        UniqueConstraint("game_id", "player_id", "round_number"),
    )


class GamePhoto(Base):
    __tablename__ = "game_photos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id"), nullable=False, index=True)
    uploaded_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[str] = mapped_column(String(50), nullable=False)
    caption: Mapped[str | None] = mapped_column(String(500), nullable=True)
    context: Mapped[PhotoContext] = mapped_column(
        Enum(PhotoContext), default=PhotoContext.board, nullable=False
    )
    round_id: Mapped[int | None] = mapped_column(ForeignKey("rounds.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    game: Mapped[Game] = relationship()
    uploaded_by: Mapped[User] = relationship()
    round: Mapped[Round | None] = relationship()
