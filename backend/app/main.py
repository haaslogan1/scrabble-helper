from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from app import admin as admin_service
from app import auth, avatars, dictionary, email_verification, feedback, friends, notifications, photos, services, stats
from app.config import settings
from app.database import Base, SessionLocal, engine, get_db
from app.email_send import smtp_configured
from app.models import GameStatus, User
from app.realtime import game_connections
from app.schemas import (
    FinalizeGame,
    FeedbackCreate,
    FeedbackOut,
    FeedbackReviewUpdate,
    DictionaryCheckOut,
    FriendAdd,
    FriendOut,
    FriendRequestOut,
    FriendSendOut,
    GameCreate,
    GamePhotoOut,
    GamePlayersUpdate,
    HomeOut,
    LoginRequest,
    NotificationListOut,
    NotificationOut,
    PlayerCreate,
    PlayerOut,
    RegisterRequest,
    RegisterSendCodeRequest,
    RegisterSendCodeResponse,
    RegisterVerifyRequest,
    TurnOrderUpdate,
    TurnRecord,
    UserOut,
    UserSearchOut,
    UsernameUpdate,
)

STATIC_DIR = Path(__file__).resolve().parents[1] / "frontend" / "dist"
logger = logging.getLogger(__name__)


def _ws_current_user(websocket: WebSocket, db: Session) -> User:
    if settings.dev_auth_bypass:
        user = db.query(User).filter(User.email == settings.dev_user_email).one_or_none()
        if user is None:
            user = User(
                email=settings.dev_user_email,
                name=settings.dev_user_name,
                provider="dev",
                provider_sub="dev-local",
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        return user
    session = websocket.scope.get("session") or {}
    user_id = session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


async def _broadcast_game_state(game_id: int) -> None:
    with SessionLocal() as db:
        state = services.game_state_broadcast(db, game_id)
    await game_connections.broadcast(f"game:{game_id}", state)


_REVISION_ALIASES = {
    "004_notifications_friend_requests": "004_notifications",
}


def _repair_revision_stamp() -> None:
    if "alembic_version" not in inspect(engine).get_table_names():
        return
    with engine.begin() as conn:
        row = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none()
        if row and row in _REVISION_ALIASES:
            canonical = _REVISION_ALIASES[row]
            conn.execute(
                text("UPDATE alembic_version SET version_num = :canonical"),
                {"canonical": canonical},
            )
            logger.warning("Repaired alembic revision stamp %s -> %s", row, canonical)


def run_migrations() -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    alembic_cfg = Config(str(backend_dir / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(backend_dir / "alembic"))
    if "users" not in inspect(engine).get_table_names():
        Base.metadata.create_all(bind=engine)
    _repair_revision_stamp()
    command.upgrade(alembic_cfg, "head")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        run_migrations()
        with SessionLocal() as db:
            auth.bootstrap_admin(db)
        if settings.email_verification_enabled and not smtp_configured():
            if settings.email_verification_dev_expose_code:
                logger.warning(
                    "Email verification enabled but SMTP is not configured; "
                    "dev codes will be exposed in API responses."
                )
            else:
                logger.error(
                    "Email verification enabled but SMTP is not configured. "
                    "Set SMTP_HOST and SMTP_FROM (Fly secrets) or registration will fail."
                )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Database startup failed")
        raise
    yield


app = FastAPI(title="Scrabble Helper", lifespan=lifespan)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    https_only=settings.cookie_secure,
    same_site="lax",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, settings.base_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health(db: bool = Query(False)) -> dict[str, str]:
    if not db:
        return {"status": "ok"}
    try:
        db_session = SessionLocal()
        db_session.execute(text("SELECT 1"))
        db_session.close()
        return {"status": "ok", "db": "ok"}
    except Exception:
        raise HTTPException(status_code=503, detail="Database unavailable")


@app.get("/auth/config")
def auth_config():
    return auth.auth_config()


@app.get("/auth/dev-login")
def auth_dev_login(request: Request, db: Session = Depends(get_db)):
    return auth.dev_login(request, db)


@app.post("/auth/register", response_model=UserOut)
def auth_register(body: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    if not settings.local_auth_enabled:
        raise HTTPException(status_code=404, detail="Not found")
    if settings.email_verification_enabled:
        raise HTTPException(
            status_code=400,
            detail="Email verification is required. Request a verification code first.",
        )
    user = auth.register_basic_user(
        db, request, email=body.email, password=body.password, name=body.name
    )
    return avatars.user_out(user)


@app.post("/auth/register/send-code", response_model=RegisterSendCodeResponse)
def auth_register_send_code(body: RegisterSendCodeRequest, db: Session = Depends(get_db)):
    if not settings.local_auth_enabled or not settings.email_verification_enabled:
        raise HTTPException(status_code=404, detail="Not found")
    return email_verification.request_registration_code(
        db, email=body.email, password=body.password, name=body.name
    )


@app.post("/auth/register/verify", response_model=UserOut)
def auth_register_verify(
    body: RegisterVerifyRequest, request: Request, db: Session = Depends(get_db)
):
    if not settings.local_auth_enabled or not settings.email_verification_enabled:
        raise HTTPException(status_code=404, detail="Not found")
    user = email_verification.complete_registration(
        db, request.session, email=body.email, code=body.code
    )
    return avatars.user_out(user)


@app.post("/auth/login", response_model=UserOut)
def auth_login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    if not settings.local_auth_enabled:
        raise HTTPException(status_code=404, detail="Not found")
    user = auth.login_basic_user(db, request, email=body.email, password=body.password)
    return avatars.user_out(user)


@app.get("/auth/login/google")
async def login_google(request: Request):
    return await auth.google_login(request)


@app.get("/auth/callback/google")
async def callback_google(request: Request, db: Session = Depends(get_db)):
    return await auth.google_callback(request, db)


@app.post("/auth/logout")
def auth_logout(request: Request):
    return auth.logout(request)


@app.get("/auth/me", response_model=UserOut)
def auth_me(request: Request, db: Session = Depends(get_db)) -> UserOut:
    user = auth.get_current_user(request, db)
    return avatars.user_out(user)


@app.patch("/api/me", response_model=UserOut)
def api_update_me(
    body: UsernameUpdate, request: Request, db: Session = Depends(get_db)
) -> UserOut:
    user = auth.get_current_user(request, db)
    updated = friends.set_username(db, user, body.username)
    return avatars.user_out(updated)


@app.post("/api/me/avatar", response_model=UserOut)
async def api_upload_avatar(
    request: Request,
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
):
    user = auth.get_current_user(request, db)
    return await avatars.upload_avatar(db, user, file)


@app.delete("/api/me/avatar", response_model=UserOut)
def api_delete_avatar(request: Request, db: Session = Depends(get_db)) -> UserOut:
    user = auth.get_current_user(request, db)
    return avatars.delete_avatar(db, user)


@app.get("/api/friends", response_model=list[FriendOut])
def api_list_friends(request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    return friends.list_friends(db, user.id)


@app.post("/api/friends", response_model=FriendSendOut)
def api_add_friend(body: FriendAdd, request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    return friends.add_friend(
        db, user.id, friend_user_id=body.user_id, username=body.username
    )


@app.get("/api/friends/requests/incoming", response_model=list[FriendRequestOut])
def api_incoming_friend_requests(request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    return friends.list_incoming_requests(db, user.id)


@app.post("/api/friends/requests/{request_id}/accept", response_model=FriendOut)
def api_accept_friend_request(
    request_id: int, request: Request, db: Session = Depends(get_db)
):
    user = auth.get_current_user(request, db)
    return friends.accept_friend_request(db, user.id, request_id)


@app.post("/api/friends/requests/{request_id}/deny")
def api_deny_friend_request(
    request_id: int, request: Request, db: Session = Depends(get_db)
):
    user = auth.get_current_user(request, db)
    return friends.decline_friend_request(db, user.id, request_id)


@app.get("/api/notifications", response_model=NotificationListOut)
def api_list_notifications(request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    return {
        "notifications": notifications.list_notifications(db, user.id),
        "unread_count": notifications.unread_count(db, user.id),
    }


@app.get("/api/notifications/unread-count")
def api_unread_notification_count(request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    return {"unread_count": notifications.unread_count(db, user.id)}


@app.post("/api/notifications/{notification_id}/read", response_model=NotificationOut)
def api_mark_notification_read(
    notification_id: int, request: Request, db: Session = Depends(get_db)
):
    user = auth.get_current_user(request, db)
    return notifications.mark_read(db, user.id, notification_id)


@app.post("/api/notifications/{notification_id}/dismiss")
def api_dismiss_notification(
    notification_id: int, request: Request, db: Session = Depends(get_db)
):
    user = auth.get_current_user(request, db)
    return notifications.dismiss(db, user.id, notification_id)


@app.post("/api/notifications/read-all")
def api_mark_all_notifications_read(request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    return notifications.mark_all_read(db, user.id)


@app.post("/api/notifications/{notification_id}/accept", response_model=FriendOut)
def api_accept_notification_friend_request(
    notification_id: int, request: Request, db: Session = Depends(get_db)
):
    user = auth.get_current_user(request, db)
    return friends.accept_friend_request_from_notification(db, user.id, notification_id)


@app.post("/api/notifications/{notification_id}/deny")
def api_deny_notification_friend_request(
    notification_id: int, request: Request, db: Session = Depends(get_db)
):
    user = auth.get_current_user(request, db)
    return friends.decline_friend_request_from_notification(db, user.id, notification_id)


@app.delete("/api/friends/{friend_user_id}")
def api_remove_friend(
    friend_user_id: int, request: Request, db: Session = Depends(get_db)
):
    user = auth.get_current_user(request, db)
    friends.remove_friend(db, user.id, friend_user_id)
    return {"status": "ok"}


@app.get("/api/friends/suggestions", response_model=list[UserSearchOut])
def api_friend_suggestions(request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    return friends.friend_suggestions(db, user.id)


@app.get("/api/users/search", response_model=list[UserSearchOut])
def api_search_users(
    request: Request,
    db: Session = Depends(get_db),
    q: str = Query(default="", min_length=1),
):
    user = auth.get_current_user(request, db)
    return friends.search_users(db, user.id, q)


@app.get("/api/admin/users")
def api_admin_users(request: Request, db: Session = Depends(get_db)):
    auth.require_admin(request, db)
    return admin_service.list_users(db)


@app.get("/api/admin/games")
def api_admin_games(
    request: Request,
    db: Session = Depends(get_db),
    owner_email: str | None = Query(default=None),
):
    auth.require_admin(request, db)
    return admin_service.list_games(db, owner_email=owner_email)


@app.delete("/api/admin/games/{game_id}")
def api_admin_delete_game(game_id: int, request: Request, db: Session = Depends(get_db)):
    auth.require_admin(request, db)
    return {"deleted": admin_service.delete_game(db, game_id)}


@app.delete("/api/admin/users/{user_id}/games")
def api_admin_delete_user_games(user_id: int, request: Request, db: Session = Depends(get_db)):
    auth.require_admin(request, db)
    return {"deleted_count": admin_service.delete_all_games_for_user(db, user_id)}


@app.delete("/api/admin/users/by-email/{email}/games")
def api_admin_delete_user_games_by_email(
    email: str, request: Request, db: Session = Depends(get_db)
):
    auth.require_admin(request, db)
    return {"deleted_count": admin_service.delete_all_games_for_email(db, email)}


@app.get("/api/admin/feedback", response_model=list[FeedbackOut])
def api_admin_list_feedback(
    request: Request,
    db: Session = Depends(get_db),
    reviewed: bool | None = Query(default=None),
):
    auth.require_admin(request, db)
    return admin_service.list_feedback(db, reviewed=reviewed)


@app.patch("/api/admin/feedback/{feedback_id}", response_model=FeedbackOut)
def api_admin_update_feedback(
    feedback_id: int,
    body: FeedbackReviewUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    auth.require_admin(request, db)
    return admin_service.update_feedback_reviewed(db, feedback_id, body.reviewed)


@app.post("/api/feedback", status_code=204)
def api_submit_feedback(
    body: FeedbackCreate, request: Request, db: Session = Depends(get_db)
):
    user = auth.get_current_user(request, db)
    feedback.submit_feedback(db, user, body)
    return Response(status_code=204)


@app.get("/api/home", response_model=HomeOut)
def api_home(request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    return services.home_summary(db, user.id)


@app.get("/api/dictionary/check/{word}", response_model=DictionaryCheckOut)
def api_dictionary_check(word: str, request: Request, db: Session = Depends(get_db)):
    auth.get_current_user(request, db)
    normalized = dictionary.normalize_word(word)
    if normalized is None:
        return DictionaryCheckOut(word=word.strip().upper() or word.strip(), valid=False)
    return DictionaryCheckOut(word=normalized, valid=dictionary.is_valid_word(word))


@app.get("/api/players", response_model=list[PlayerOut])
def api_list_players(request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    players = services.list_players(db, user.id)
    return [friends.player_out_extra(db, user.id, p) for p in players]


@app.post("/api/players", response_model=PlayerOut)
def api_create_player(
    body: PlayerCreate, request: Request, db: Session = Depends(get_db)
):
    user = auth.get_current_user(request, db)
    player = services.create_player(db, user.id, body.name)
    return friends.player_out_extra(db, user.id, player)


@app.post("/api/games")
def api_create_game(
    body: GameCreate, request: Request, db: Session = Depends(get_db)
):
    user = auth.get_current_user(request, db)
    settings_dict = body.settings.model_dump() if body.settings else None
    game = services.create_game(db, user.id, settings_dict)
    return {"id": game.id, "status": game.status.value, "settings": game.settings}


@app.put("/api/games/{game_id}/players")
async def api_set_players(
    game_id: int,
    body: GamePlayersUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    user = auth.get_current_user(request, db)
    game = services.set_game_players(db, user.id, game_id, body.player_ids)
    await _broadcast_game_state(game.id)
    return services.game_state(db, user.id, game.id)


@app.post("/api/games/{game_id}/turn-order")
async def api_turn_order(
    game_id: int,
    body: TurnOrderUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    user = auth.get_current_user(request, db)
    game = services.set_turn_order(db, user.id, game_id, body.player_ids)
    await _broadcast_game_state(game.id)
    return services.game_state(db, user.id, game.id)


@app.post("/api/games/{game_id}/random-first")
async def api_random_first(game_id: int, request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    game = services.random_first_player(db, user.id, game_id)
    await _broadcast_game_state(game.id)
    return services.game_state(db, user.id, game.id)


@app.post("/api/games/{game_id}/begin")
async def api_begin(game_id: int, request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    game = services.begin_game(db, user.id, game_id)
    await _broadcast_game_state(game.id)
    return services.game_state(db, user.id, game.id)


@app.post("/api/games/{game_id}/turns")
async def api_record_turn(
    game_id: int,
    body: TurnRecord,
    request: Request,
    db: Session = Depends(get_db),
):
    user = auth.get_current_user(request, db)
    services.record_turn(
        db,
        user.id,
        game_id,
        points=body.points,
        word=body.word,
        play_type=body.play_type,
        timer_elapsed_sec=body.timer_elapsed_sec,
    )
    await _broadcast_game_state(game_id)
    return services.game_state(db, user.id, game_id)


@app.post("/api/games/{game_id}/next-player")
async def api_next_player(game_id: int, request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    services.advance_turn(db, user.id, game_id)
    await _broadcast_game_state(game_id)
    return services.game_state(db, user.id, game_id)


@app.post("/api/games/{game_id}/end")
async def api_end_game(game_id: int, request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    services.end_game(db, user.id, game_id)
    await _broadcast_game_state(game_id)
    return services.game_state(db, user.id, game_id)


@app.post("/api/games/{game_id}/ack-inactivity")
async def api_ack_inactivity(game_id: int, request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    services.ack_inactivity(db, user.id, game_id)
    await _broadcast_game_state(game_id)
    return services.game_state(db, user.id, game_id)


@app.post("/api/games/{game_id}/finalize")
async def api_finalize(
    game_id: int,
    body: FinalizeGame,
    request: Request,
    db: Session = Depends(get_db),
):
    user = auth.get_current_user(request, db)
    services.finalize_game(db, user.id, game_id, body.rack_adjustments)
    await _broadcast_game_state(game_id)
    return services.game_detail(db, user.id, game_id)


@app.get("/api/games/{game_id}/state")
def api_game_state(game_id: int, request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    return services.game_state(db, user.id, game_id)


@app.get("/api/games/{game_id}/photos", response_model=list[GamePhotoOut])
def api_list_game_photos(game_id: int, request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    return photos.list_game_photos(db, user.id, game_id)


@app.post("/api/games/{game_id}/photos", response_model=GamePhotoOut, status_code=201)
async def api_upload_game_photo(
    game_id: int,
    request: Request,
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
    caption: str | None = Form(default=None),
    context: str | None = Form(default=None),
    round_id: int | None = Form(default=None),
):
    user = auth.get_current_user(request, db)
    return await photos.upload_game_photo(
        db, user, game_id, file, caption=caption, context=context, round_id=round_id
    )


@app.delete("/api/games/{game_id}/photos/{photo_id}", status_code=204)
def api_delete_game_photo(
    game_id: int, photo_id: int, request: Request, db: Session = Depends(get_db)
):
    user = auth.get_current_user(request, db)
    photos.delete_game_photo(db, user.id, game_id, photo_id)
    return Response(status_code=204)


@app.get("/api/games/{game_id}")
def api_game_detail(game_id: int, request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    return services.game_detail(db, user.id, game_id)


@app.get("/api/games")
def api_list_games(
    request: Request,
    db: Session = Depends(get_db),
    status: str | None = Query(default=None),
):
    user = auth.get_current_user(request, db)
    status_enum = GameStatus(status) if status else None
    games = services.list_games(db, user.id, status_enum)
    result = []
    for game in games:
        ordered = sorted(game.game_players, key=lambda gp: gp.turn_order)
        winner = next((gp for gp in ordered if gp.won), None)
        result.append(
            {
                "id": game.id,
                "status": game.status.value,
                "played_date": game.played_date.isoformat() if game.played_date else None,
                "completed_at": game.completed_at.isoformat() if game.completed_at else None,
                "winner": winner.player.name if winner else None,
            }
        )
    return result


@app.get("/api/leaderboard")
def api_leaderboard(
    request: Request,
    db: Session = Depends(get_db),
    scope: str = Query(default="all"),
):
    if scope not in ("all", "friends", "manual"):
        raise HTTPException(status_code=400, detail="Invalid scope")
    user = auth.get_current_user(request, db)
    return stats.all_stats(db, user.id, scope)  # type: ignore[arg-type]


@app.websocket("/api/games/{game_id}/watch")
async def ws_game_watch(websocket: WebSocket, game_id: int):
    room = f"game:{game_id}"
    db = SessionLocal()
    connected = False
    try:
        user = _ws_current_user(websocket, db)
        game, role = services.get_game_access(db, user.id, game_id)
        state = services._build_game_state(game, role)
        await game_connections.connect(room, websocket)
        connected = True
        await websocket.send_json(state)
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except HTTPException as exc:
        await websocket.close(code=4403 if exc.status_code == 403 else 4404)
    except Exception:
        logger.exception("websocket error for game %s", game_id)
        if connected:
            await websocket.close(code=1011)
        else:
            await websocket.close(code=1011)
    finally:
        if connected:
            await game_connections.disconnect(room, websocket)
        db.close()


if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def spa_fallback(full_path: str):
        if full_path.startswith("api/") or full_path.startswith("auth/"):
            return {"detail": "Not found"}
        index = STATIC_DIR / "index.html"
        if index.exists():
            return FileResponse(index)
        return {"detail": "Frontend not built"}
