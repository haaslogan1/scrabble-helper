from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from app import admin as admin_service
from app import auth, email_verification, services, stats
from app.config import settings
from app.database import Base, SessionLocal, engine, get_db
from app.models import GameStatus, User
from app.schemas import (
    FinalizeGame,
    GameCreate,
    GamePlayersUpdate,
    HomeOut,
    LoginRequest,
    PlayerCreate,
    PlayerOut,
    RegisterRequest,
    RegisterSendCodeRequest,
    RegisterSendCodeResponse,
    RegisterVerifyRequest,
    TurnOrderUpdate,
    TurnRecord,
    UserOut,
)

STATIC_DIR = Path(__file__).resolve().parents[1] / "frontend" / "dist"
logger = logging.getLogger(__name__)


def run_migrations() -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    alembic_cfg = Config(str(backend_dir / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(backend_dir / "alembic"))
    command.upgrade(alembic_cfg, "head")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        Base.metadata.create_all(bind=engine)
        run_migrations()
        with SessionLocal() as db:
            auth.bootstrap_admin(db)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Database unavailable at startup: %s", exc)
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
def health() -> dict[str, str]:
    return {"status": "ok"}


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
    return auth.register_basic_user(
        db, request, email=body.email, password=body.password, name=body.name
    )


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
    return email_verification.complete_registration(
        db, request.session, email=body.email, code=body.code
    )


@app.post("/auth/login", response_model=UserOut)
def auth_login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    if not settings.local_auth_enabled:
        raise HTTPException(status_code=404, detail="Not found")
    return auth.login_basic_user(db, request, email=body.email, password=body.password)


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
def auth_me(request: Request, db: Session = Depends(get_db)) -> User:
    return auth.get_current_user(request, db)


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


@app.get("/api/home", response_model=HomeOut)
def api_home(request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    return services.home_summary(db, user.id)


@app.get("/api/players", response_model=list[PlayerOut])
def api_list_players(request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    return services.list_players(db, user.id)


@app.post("/api/players", response_model=PlayerOut)
def api_create_player(
    body: PlayerCreate, request: Request, db: Session = Depends(get_db)
):
    user = auth.get_current_user(request, db)
    return services.create_player(db, user.id, body.name)


@app.post("/api/games")
def api_create_game(
    body: GameCreate, request: Request, db: Session = Depends(get_db)
):
    user = auth.get_current_user(request, db)
    settings_dict = body.settings.model_dump() if body.settings else None
    game = services.create_game(db, user.id, settings_dict)
    return {"id": game.id, "status": game.status.value, "settings": game.settings}


@app.put("/api/games/{game_id}/players")
def api_set_players(
    game_id: int,
    body: GamePlayersUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    user = auth.get_current_user(request, db)
    game = services.set_game_players(db, user.id, game_id, body.player_ids)
    return services.game_state(db, user.id, game.id)


@app.post("/api/games/{game_id}/turn-order")
def api_turn_order(
    game_id: int,
    body: TurnOrderUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    user = auth.get_current_user(request, db)
    game = services.set_turn_order(db, user.id, game_id, body.player_ids)
    return services.game_state(db, user.id, game.id)


@app.post("/api/games/{game_id}/random-first")
def api_random_first(game_id: int, request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    game = services.random_first_player(db, user.id, game_id)
    return services.game_state(db, user.id, game.id)


@app.post("/api/games/{game_id}/begin")
def api_begin(game_id: int, request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    game = services.begin_game(db, user.id, game_id)
    return services.game_state(db, user.id, game.id)


@app.post("/api/games/{game_id}/turns")
def api_record_turn(
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
    return services.game_state(db, user.id, game_id)


@app.post("/api/games/{game_id}/next-player")
def api_next_player(game_id: int, request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    services.advance_turn(db, user.id, game_id)
    return services.game_state(db, user.id, game_id)


@app.post("/api/games/{game_id}/end")
def api_end_game(game_id: int, request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    services.end_game(db, user.id, game_id)
    return services.game_state(db, user.id, game_id)


@app.post("/api/games/{game_id}/finalize")
def api_finalize(
    game_id: int,
    body: FinalizeGame,
    request: Request,
    db: Session = Depends(get_db),
):
    user = auth.get_current_user(request, db)
    services.finalize_game(db, user.id, game_id, body.rack_adjustments)
    return services.game_detail(db, user.id, game_id)


@app.get("/api/games/{game_id}/state")
def api_game_state(game_id: int, request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    return services.game_state(db, user.id, game_id)


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
def api_leaderboard(request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    return stats.all_stats(db, user.id)


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
