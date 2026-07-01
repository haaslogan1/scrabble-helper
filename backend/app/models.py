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


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False, default="google")
    provider_sub: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    totp_secret: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    players: Mapped[list[Player]] = relationship(back_populates="owner")
    games: Mapped[list[Game]] = relationship(back_populates="owner")

    __table_args__ = (UniqueConstraint("provider", "provider_sub"),)


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
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    owner: Mapped[User] = relationship(back_populates="players")

    __table_args__ = (UniqueConstraint("owner_user_id", "name"),)


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
