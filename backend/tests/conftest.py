from __future__ import annotations

import json
import os
import sys
import time
import uuid
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_scrabble_helper.db")
os.environ.setdefault("DEV_AUTH_BYPASS", "true")
os.environ.setdefault("SESSION_SECRET", "test-secret")

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import User


def _stamp_db_head() -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    cfg = Config(str(backend_dir / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend_dir / "alembic"))
    command.stamp(cfg, "head")


def _debug_log(hypothesis_id: str, message: str, data: dict | None = None) -> None:
    # #region agent log
    log_path = Path(__file__).resolve().parents[2] / "debug-378b54.log"
    payload = {
        "sessionId": "378b54",
        "runId": os.environ.get("CI", "local"),
        "hypothesisId": hypothesis_id,
        "location": "tests/conftest.py",
        "message": message,
        "data": data or {},
        "timestamp": int(time.time() * 1000),
    }
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload) + "\n")
    # #endregion


def _reset_schema() -> None:
    dialect = engine.dialect.name
    _debug_log("H-A", "reset_schema start", {"dialect": dialect})
    if dialect == "postgresql":
        with engine.connect() as conn:
            conn.execute(text("DROP SCHEMA public CASCADE"))
            conn.execute(text("CREATE SCHEMA public"))
            conn.commit()
        engine.dispose()
        _debug_log("H-B", "postgresql engine pool disposed after schema reset")
    else:
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    _stamp_db_head()
    _debug_log(
        "H-A",
        "reset_schema complete",
        {"tables": sorted(Base.metadata.tables.keys())},
    )


@pytest.fixture(scope="session", autouse=True)
def reset_db():
    """Fresh schema each pytest invocation (local SQLite file otherwise accumulates users)."""
    _reset_schema()
    yield


@pytest.fixture(autouse=True)
def skip_lifespan_migrations(monkeypatch):
    """Tests build schema via create_all; avoid Alembic upgrade conflicts on PostgreSQL."""
    monkeypatch.setattr("app.main.run_migrations", lambda: None)


@pytest.fixture()
def db() -> Session:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setattr(settings, "dev_auth_bypass", True)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def user(db: Session) -> User:
    existing = db.query(User).filter(User.email == settings.dev_user_email).one_or_none()
    if existing:
        return existing
    user = User(
        email=settings.dev_user_email,
        name=settings.dev_user_name,
        provider="dev",
        provider_sub="dev-test",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def auth_client(monkeypatch):
    monkeypatch.setattr(settings, "dev_auth_bypass", False)
    monkeypatch.setattr(settings, "local_auth_enabled", True)
    monkeypatch.setattr(settings, "email_verification_enabled", True)
    monkeypatch.setattr(settings, "email_verification_dev_expose_code", True)
    from tests.qa_gameplay import register_basic_user

    with TestClient(app) as test_client:
        register_basic_user(
            test_client, email=f"basic-{uuid.uuid4().hex[:8]}@test.local"
        )
        yield test_client


@pytest.fixture
def admin_client(monkeypatch):
    from app import auth
    from tests.qa_gameplay import login_basic_user

    monkeypatch.setattr(settings, "dev_auth_bypass", False)
    monkeypatch.setattr(settings, "local_auth_enabled", True)
    monkeypatch.setattr(settings, "email_verification_enabled", True)
    monkeypatch.setattr(settings, "email_verification_dev_expose_code", True)
    monkeypatch.setattr(settings, "admin_email", "admin@test.local")
    monkeypatch.setattr(settings, "admin_password", "AdminPass123")
    with TestClient(app) as test_client:
        with SessionLocal() as db:
            auth.bootstrap_admin(db)
        login_basic_user(test_client, email="admin@test.local", password="AdminPass123")
        yield test_client


@pytest.fixture
def basic_client(monkeypatch):
    """Unauthenticated strict client for registering a second basic user."""
    monkeypatch.setattr(settings, "dev_auth_bypass", False)
    monkeypatch.setattr(settings, "local_auth_enabled", True)
    monkeypatch.setattr(settings, "email_verification_enabled", True)
    monkeypatch.setattr(settings, "email_verification_dev_expose_code", True)
    with TestClient(app) as test_client:
        yield test_client
