"""Single-session enforcement tests."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request
from starlette.websockets import WebSocketDisconnect

from app import auth
from app.config import settings
from app.main import app
from app.models import User
from app.passwords import hash_password
from tests.qa_gameplay import (
    DEFAULT_PASSWORD,
    connect_game_watch_ws,
    register_basic_user,
    setup_and_begin_game,
)


def _make_client(monkeypatch, *, email_verification: bool = True) -> TestClient:
    monkeypatch.setattr(settings, "dev_auth_bypass", False)
    monkeypatch.setattr(settings, "local_auth_enabled", True)
    monkeypatch.setattr(settings, "email_verification_enabled", email_verification)
    monkeypatch.setattr(settings, "email_verification_dev_expose_code", True)
    return TestClient(app)


def _request_with_session(session: dict) -> Request:
    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [],
        "session": session,
    }
    return Request(scope, receive)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("user_agent", "expected"),
    [
        ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0)", "mobile"),
        ("Mozilla/5.0 (Linux; Android 14)", "mobile"),
        ("Mozilla/5.0 (iPad; CPU OS 17_0)", "tablet"),
        ("Mozilla/5.0 (Tablet; rv:109.0)", "tablet"),
        ("Mozilla/5.0 (Windows NT 10.0)", "computer"),
        (None, None),
    ],
)
def test_parse_device_label(user_agent, expected):
    assert auth.parse_device_label(user_agent) == expected


@pytest.mark.unit
def test_validate_session_version_accepts_legacy_cookie_when_user_version_zero():
    request = _request_with_session({"user_id": 1})
    user = SimpleNamespace(session_version=0)
    auth.validate_session_version(request, user)


@pytest.mark.unit
def test_validate_session_version_rejects_missing_version_when_user_has_active_session():
    request = _request_with_session({"user_id": 1})
    user = SimpleNamespace(session_version=2)
    with pytest.raises(HTTPException) as exc:
        auth.validate_session_version(request, user)
    assert exc.value.status_code == 401
    assert exc.value.detail["code"] == "session_superseded"


@pytest.mark.unit
def test_validate_session_version_rejects_stale_version():
    request = _request_with_session({"user_id": 1, "session_version": 1})
    user = SimpleNamespace(session_version=2)
    with pytest.raises(HTTPException):
        auth.validate_session_version(request, user)


@pytest.mark.unit
def test_validate_ws_session_version_matches_http_rules():
    user = SimpleNamespace(session_version=1)
    auth.validate_ws_session_version({"user_id": 1, "session_version": 1}, user)
    with pytest.raises(HTTPException):
        auth.validate_ws_session_version({"user_id": 1}, user)


@pytest.mark.integration
def test_single_session_login_replaces_prior(monkeypatch):
    email = f"single-{uuid.uuid4().hex[:8]}@test.local"
    laptop_ua = "Mozilla/5.0 (Windows NT 10.0) LaptopBrowser"
    phone_ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0)"

    with _make_client(monkeypatch) as client1:
        register_basic_user(client1, email=email)
        assert client1.get("/auth/me").status_code == 200

        with _make_client(monkeypatch) as client2:
            login2 = client2.post(
                "/auth/login",
                json={"email": email, "password": DEFAULT_PASSWORD},
                headers={"User-Agent": phone_ua},
            )
            assert login2.status_code == 200
            body2 = login2.json()
            assert body2["session_replaced"] is True
            assert body2["session_replaced_device"] == "computer"
            assert client2.get("/auth/me").status_code == 200

            superseded = client1.get("/auth/me")
            assert superseded.status_code == 401
            assert superseded.json()["detail"]["code"] == "session_superseded"

            reclaim = client1.post(
                "/auth/login",
                json={"email": email, "password": DEFAULT_PASSWORD},
                headers={"User-Agent": laptop_ua},
            )
            assert reclaim.status_code == 200
            assert reclaim.json()["session_replaced"] is True
            assert reclaim.json()["session_replaced_device"] == "mobile"
            assert client1.get("/auth/me").status_code == 200
            assert client2.get("/auth/me").status_code == 401


@pytest.mark.integration
def test_first_basic_login_does_not_warn(db, monkeypatch):
    email = f"first-{uuid.uuid4().hex[:8]}@test.local"
    db.add(
        User(
            email=email,
            name="First Login",
            provider="local",
            provider_sub=email,
            password_hash=hash_password(DEFAULT_PASSWORD),
            session_version=0,
        )
    )
    db.commit()

    with _make_client(monkeypatch) as client:
        login = client.post(
            "/auth/login",
            json={"email": email, "password": DEFAULT_PASSWORD},
        )
        assert login.status_code == 200
        body = login.json()
        assert body["session_replaced"] is False
        assert body["user"]["email"] == email


@pytest.mark.integration
def test_register_does_not_warn_first_session(monkeypatch):
    email = f"new-{uuid.uuid4().hex[:8]}@test.local"
    with _make_client(monkeypatch) as client:
        send = client.post(
            "/auth/register/send-code",
            json={"email": email, "password": DEFAULT_PASSWORD, "name": "New User"},
        )
        assert send.status_code == 200
        code = send.json()["dev_code"]
        verify = client.post(
            "/auth/register/verify",
            json={"email": email, "code": code},
        )
        assert verify.status_code == 200
        assert verify.json()["session_replaced"] is False


@pytest.mark.integration
def test_direct_register_without_verification(monkeypatch):
    email = f"direct-{uuid.uuid4().hex[:8]}@test.local"
    with _make_client(monkeypatch, email_verification=False) as client:
        res = client.post(
            "/auth/register",
            json={"email": email, "password": DEFAULT_PASSWORD, "name": "Direct User"},
        )
        assert res.status_code == 200
        assert res.json()["session_replaced"] is False


@pytest.mark.integration
def test_logout_does_not_invalidate_other_clients(monkeypatch, db):
    email = f"logout-{uuid.uuid4().hex[:8]}@test.local"
    with _make_client(monkeypatch) as client1:
        register_basic_user(client1, email=email)
        user = db.query(User).filter(User.email == email).one()

        with _make_client(monkeypatch) as client2:
            login2 = client2.post(
                "/auth/login",
                json={"email": email, "password": DEFAULT_PASSWORD},
            )
            assert login2.status_code == 200
            assert client2.get("/auth/me").status_code == 200

            db.refresh(user)
            version_before_logout = user.session_version

            logout = client1.post("/auth/logout")
            assert logout.status_code == 200
            assert logout.json()["status"] == "logged_out"
            assert client1.get("/auth/me").status_code == 401
            assert client2.get("/auth/me").status_code == 200

            db.refresh(user)
            assert user.session_version == version_before_logout


@pytest.mark.integration
def test_google_callback_establishes_session(monkeypatch):
    email = f"google-{uuid.uuid4().hex[:8]}@test.local"
    sub = f"google-sub-{uuid.uuid4().hex[:8]}"

    async def fake_authorize_access_token(_request):
        return {
            "userinfo": {
                "email": email,
                "name": "Google User",
                "sub": sub,
            }
        }

    monkeypatch.setattr(
        auth.oauth.google, "authorize_access_token", fake_authorize_access_token
    )
    monkeypatch.setattr(settings, "frontend_url", "http://testserver")

    with _make_client(monkeypatch) as client:
        res = client.get("/auth/callback/google", follow_redirects=False)
        assert res.status_code == 307
        assert res.headers["location"].rstrip("/") == "http://testserver"
        assert client.get("/auth/me").status_code == 200
        assert client.get("/auth/me").json()["email"] == email


@pytest.mark.integration
def test_google_callback_redirects_with_session_replaced(monkeypatch):
    email = f"google2-{uuid.uuid4().hex[:8]}@test.local"
    sub = f"google-sub-{uuid.uuid4().hex[:8]}"

    async def fake_authorize_access_token(_request):
        return {
            "userinfo": {
                "email": email,
                "name": "Google User",
                "sub": sub,
            }
        }

    monkeypatch.setattr(
        auth.oauth.google, "authorize_access_token", fake_authorize_access_token
    )
    monkeypatch.setattr(settings, "frontend_url", "http://testserver")

    with _make_client(monkeypatch) as client1:
        first = client1.get("/auth/callback/google", follow_redirects=False)
        assert first.status_code == 307
        assert "session_replaced" not in first.headers["location"]

        with _make_client(monkeypatch) as client2:
            second = client2.get(
                "/auth/callback/google",
                follow_redirects=False,
                headers={"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0)"},
            )
            assert second.status_code == 307
            location = second.headers["location"]
            assert "session_replaced=1" in location
            assert "device=computer" in location


@pytest.mark.integration
def test_websocket_rejects_superseded_session(monkeypatch):
    email = f"ws-{uuid.uuid4().hex[:8]}@test.local"
    with _make_client(monkeypatch) as client1:
        register_basic_user(client1, email=email)
        game_id = setup_and_begin_game(client1, ["Host", "Guest"])

        with _make_client(monkeypatch) as client2:
            assert (
                client2.post(
                    "/auth/login",
                    json={"email": email, "password": DEFAULT_PASSWORD},
                ).status_code
                == 200
            )

            with pytest.raises(WebSocketDisconnect):
                with client1.websocket_connect(f"/api/games/{game_id}/watch"):
                    pass

            with connect_game_watch_ws(client2, game_id) as ws:
                assert ws.receive_json()["id"] == game_id
