from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class PlayerCreate(BaseModel):
    name: str


class PlayerOut(BaseModel):
    id: int
    name: str
    linked_user_id: int | None = None
    is_friend: bool = False
    mutual: bool | None = None
    is_self: bool = False

    model_config = {"from_attributes": True}


class FriendOut(BaseModel):
    id: int
    username: str | None
    name: str
    mutual: bool
    avatar_url: str | None = None


class FriendSendOut(BaseModel):
    id: int
    username: str | None
    name: str
    request_id: int | None = None
    status: str
    mutual: bool | None = None


class FriendRequestOut(BaseModel):
    id: int
    from_user: UserSearchOut
    created_at: str


class NotificationOut(BaseModel):
    id: int
    type: str
    title: str
    body: str
    payload: dict[str, Any]
    read: bool
    created_at: str


class NotificationListOut(BaseModel):
    notifications: list[NotificationOut]
    unread_count: int


class FriendAdd(BaseModel):
    user_id: int | None = None
    username: str | None = None


class UserSearchOut(BaseModel):
    id: int
    username: str | None
    name: str
    reason: str | None = None
    avatar_url: str | None = None


class UsernameUpdate(BaseModel):
    username: str


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
    username: str | None = None
    is_admin: bool = False
    avatar_url: str | None = None
    has_custom_avatar: bool = False
    provider: str = "google"

    model_config = {"from_attributes": True}


class GamePhotoOut(BaseModel):
    id: int
    url: str
    caption: str | None
    context: str
    created_at: datetime
    uploaded_by_name: str


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


class AuthLoginResponse(BaseModel):
    user: UserOut
    session_replaced: bool = False
    session_replaced_device: Literal["mobile", "tablet", "computer"] | None = None


class HomeOut(BaseModel):
    completed_games: int
    in_progress_games: int
    saved_players: int
    participating_in_progress_games: int


class ParticipatingGameOut(BaseModel):
    id: int
    status: str
    role: str
    owner_name: str
    last_activity_at: str | None = None
    can_finalize: bool = False
    can_abandon: bool = False
    resume_url: str


class FeedbackCreate(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    category: Literal["bug", "idea", "other"] | None = None
    page_url: str | None = Field(default=None, max_length=512)
    game_id: int | None = None


class FeedbackReviewUpdate(BaseModel):
    reviewed: bool


class FeedbackOut(BaseModel):
    id: int
    user_email: str
    category: str | None
    message: str
    page_url: str | None
    game_id: int | None
    reviewed: bool
    created_at: str


class DictionaryCheckOut(BaseModel):
    word: str
    valid: bool
