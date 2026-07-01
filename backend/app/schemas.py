from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PlayerCreate(BaseModel):
    name: str


class PlayerOut(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class GameSettings(BaseModel):
    minutes_per_turn: int = 3
    input_mode: str = "points"
    show_live_leaderboard: bool = True


class GameCreate(BaseModel):
    settings: GameSettings | None = None


class GamePlayersUpdate(BaseModel):
    player_ids: list[int]


class TurnOrderUpdate(BaseModel):
    player_ids: list[int]


class TurnRecord(BaseModel):
    points: float | None = None
    word: str | None = None
    play_type: str = "score"
    timer_elapsed_sec: int | None = None


class FinalizeGame(BaseModel):
    rack_adjustments: dict[str, float] = Field(default_factory=dict)


class UserOut(BaseModel):
    id: int
    email: str
    name: str
    is_admin: bool = False

    model_config = {"from_attributes": True}


class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str = ""


class RegisterSendCodeRequest(BaseModel):
    email: str
    password: str
    name: str = ""


class RegisterVerifyRequest(BaseModel):
    email: str
    code: str


class RegisterSendCodeResponse(BaseModel):
    message: str
    expires_in_minutes: int
    dev_code: str | None = None


class LoginRequest(BaseModel):
    email: str
    password: str


class HomeOut(BaseModel):
    completed_games: int
    in_progress_games: int
    saved_players: int
