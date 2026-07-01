from __future__ import annotations

import os
import sys
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_scrabble_helper.db")
os.environ.setdefault("DEV_AUTH_BYPASS", "true")
os.environ.setdefault("SESSION_SECRET", "test-secret")

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import User


@pytest.fixture(scope="session", autouse=True)
def reset_db():
    """Fresh schema each pytest invocation (local SQLite file otherwise accumulates users)."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


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
