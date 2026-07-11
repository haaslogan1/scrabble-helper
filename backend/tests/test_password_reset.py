"""Forgot-password / password-reset API tests."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.database import SessionLocal
from app.main import app
from app.models import PasswordReset, User
from app.passwords import verify_password
from tests.qa_gameplay import DEFAULT_PASSWORD, register_basic_user

GENERIC_SNIPPET = "if an account with that email can reset"


@pytest.fixture
def reset_client(monkeypatch):
    monkeypatch.setattr(settings, "dev_auth_bypass", False)
    monkeypatch.setattr(settings, "local_auth_enabled", True)
    monkeypatch.setattr(settings, "email_verification_enabled", True)
    monkeypatch.setattr(settings, "email_verification_dev_expose_code", True)
    with TestClient(app) as client:
        yield client


def _request(client: TestClient, email: str):
    return client.post("/auth/password-reset/request", json={"email": email})


def _confirm(client: TestClient, email: str, code: str, new_password: str):
    return client.post(
        "/auth/password-reset/confirm",
        json={"email": email, "code": code, "new_password": new_password},
    )


@pytest.mark.integration
def test_request_unknown_email_is_generic_and_sends_nothing(reset_client, monkeypatch):
    with patch("app.password_reset.send_password_reset_email") as send:
        res = _request(reset_client, "nobody@test.local")
    assert res.status_code == 200
    body = res.json()
    assert GENERIC_SNIPPET in body["message"].lower()
    assert "dev_code" not in body or body.get("dev_code") is None
    send.assert_not_called()
    with SessionLocal() as db:
        assert db.query(PasswordReset).filter(PasswordReset.email == "nobody@test.local").count() == 0


@pytest.mark.integration
def test_request_google_only_user_sends_nothing(reset_client):
    with SessionLocal() as db:
        db.add(
            User(
                email="google-only@test.local",
                name="Google Only",
                provider="google",
                provider_sub="google-sub-1",
                password_hash=None,
            )
        )
        db.commit()

    with patch("app.password_reset.send_password_reset_email") as send:
        res = _request(reset_client, "google-only@test.local")
    assert res.status_code == 200
    assert GENERIC_SNIPPET in res.json()["message"].lower()
    send.assert_not_called()


@pytest.mark.integration
def test_request_local_user_sends_code(reset_client):
    email = "reset-local@test.local"
    register_basic_user(reset_client, email=email, name="Reset Local")
    reset_client.post("/auth/logout")

    with patch("app.password_reset.send_password_reset_email") as send:
        res = _request(reset_client, email)
    assert res.status_code == 200
    body = res.json()
    assert GENERIC_SNIPPET in body["message"].lower()
    assert body.get("dev_code")
    send.assert_called_once()
    assert send.call_args.kwargs["to_email"] == email
    assert send.call_args.kwargs["code"] == body["dev_code"]
    with SessionLocal() as db:
        row = db.query(PasswordReset).filter(PasswordReset.email == email).one()
        assert row.attempts == 0


@pytest.mark.integration
def test_request_cooldown_skips_second_send(reset_client):
    email = "reset-cooldown@test.local"
    register_basic_user(reset_client, email=email)
    reset_client.post("/auth/logout")

    with patch("app.password_reset.send_password_reset_email") as send:
        first = _request(reset_client, email)
        second = _request(reset_client, email)
    assert first.status_code == 200
    assert second.status_code == 200
    assert send.call_count == 1
    assert first.json().get("dev_code")
    assert second.json().get("dev_code") in (None, "")


@pytest.mark.integration
def test_confirm_happy_path_updates_password_and_session_version(reset_client):
    email = "reset-ok@test.local"
    register_basic_user(reset_client, email=email)
    reset_client.post("/auth/logout")

    with SessionLocal() as db:
        user = db.query(User).filter(User.email == email).one()
        version_before = user.session_version

    req = _request(reset_client, email)
    code = req.json()["dev_code"]
    new_password = "BrandNewPass99"
    confirm = _confirm(reset_client, email, code, new_password)
    assert confirm.status_code == 204

    with SessionLocal() as db:
        user = db.query(User).filter(User.email == email).one()
        assert user.session_version == version_before + 1
        assert verify_password(new_password, user.password_hash)
        assert not verify_password(DEFAULT_PASSWORD, user.password_hash)
        assert db.query(PasswordReset).filter(PasswordReset.email == email).count() == 0

    bad_old = reset_client.post("/auth/login", json={"email": email, "password": DEFAULT_PASSWORD})
    assert bad_old.status_code == 401
    new_login = reset_client.post("/auth/login", json={"email": email, "password": new_password})
    assert new_login.status_code == 200


@pytest.mark.integration
def test_confirm_invalidates_existing_session(reset_client):
    email = "reset-session@test.local"
    register_basic_user(reset_client, email=email)
    me_before = reset_client.get("/auth/me")
    assert me_before.status_code == 200

    code = _request(reset_client, email).json()["dev_code"]
    assert _confirm(reset_client, email, code, "AnotherPass12").status_code == 204

    me_after = reset_client.get("/auth/me")
    assert me_after.status_code == 401


@pytest.mark.integration
def test_confirm_wrong_code_increments_attempts(reset_client):
    email = "reset-wrong@test.local"
    register_basic_user(reset_client, email=email)
    reset_client.post("/auth/logout")
    _request(reset_client, email)

    res = _confirm(reset_client, email, "000000", "ValidPass99")
    assert res.status_code == 400
    assert "incorrect" in res.json()["detail"].lower()
    with SessionLocal() as db:
        row = db.query(PasswordReset).filter(PasswordReset.email == email).one()
        assert row.attempts == 1


@pytest.mark.integration
def test_confirm_expired_code(reset_client):
    email = "reset-expired@test.local"
    register_basic_user(reset_client, email=email)
    reset_client.post("/auth/logout")
    code = _request(reset_client, email).json()["dev_code"]

    with SessionLocal() as db:
        row = db.query(PasswordReset).filter(PasswordReset.email == email).one()
        row.expires_at = datetime.utcnow() - timedelta(minutes=1)
        db.commit()

    res = _confirm(reset_client, email, code, "ValidPass99")
    assert res.status_code == 400
    assert "expired" in res.json()["detail"].lower()


@pytest.mark.integration
def test_confirm_locks_after_five_failures(reset_client):
    email = "reset-lock@test.local"
    register_basic_user(reset_client, email=email)
    reset_client.post("/auth/logout")
    real_code = _request(reset_client, email).json()["dev_code"]

    for _ in range(5):
        res = _confirm(reset_client, email, "111111", "ValidPass99")
        assert res.status_code == 400

    with SessionLocal() as db:
        assert db.query(PasswordReset).filter(PasswordReset.email == email).count() == 0

    again = _confirm(reset_client, email, real_code, "ValidPass99")
    assert again.status_code == 400


@pytest.mark.integration
def test_confirm_weak_password_rejected(reset_client):
    email = "reset-weak@test.local"
    register_basic_user(reset_client, email=email)
    reset_client.post("/auth/logout")
    code = _request(reset_client, email).json()["dev_code"]
    res = _confirm(reset_client, email, code, "short")
    assert res.status_code == 400
    assert "password" in res.json()["detail"].lower()


@pytest.mark.integration
def test_confirm_google_only_clear_error(reset_client):
    with SessionLocal() as db:
        db.add(
            User(
                email="google-confirm@test.local",
                name="G",
                provider="google",
                provider_sub="g-sub-2",
                password_hash=None,
            )
        )
        db.commit()

    res = _confirm(reset_client, "google-confirm@test.local", "123456", "ValidPass99")
    assert res.status_code == 400
    assert "google" in res.json()["detail"].lower()


@pytest.mark.integration
def test_confirm_without_prior_request(reset_client):
    email = "reset-none@test.local"
    register_basic_user(reset_client, email=email)
    reset_client.post("/auth/logout")
    res = _confirm(reset_client, email, "123456", "ValidPass99")
    assert res.status_code == 400
    assert "no password reset" in res.json()["detail"].lower()


@pytest.mark.integration
def test_invalid_email_on_request(reset_client):
    res = _request(reset_client, "not-an-email")
    assert res.status_code == 400


@pytest.mark.integration
def test_local_auth_disabled_returns_404(monkeypatch):
    monkeypatch.setattr(settings, "dev_auth_bypass", False)
    monkeypatch.setattr(settings, "local_auth_enabled", False)
    with TestClient(app) as client:
        assert _request(client, "a@test.local").status_code == 404
        assert _confirm(client, "a@test.local", "123456", "ValidPass99").status_code == 404


@pytest.mark.integration
def test_smtp_failure_clears_pending_row(reset_client):
    email = "reset-smtp-fail@test.local"
    register_basic_user(reset_client, email=email)
    reset_client.post("/auth/logout")

    with patch(
        "app.password_reset.send_password_reset_email",
        side_effect=RuntimeError("smtp down"),
    ):
        res = _request(reset_client, email)
    assert res.status_code == 503
    with SessionLocal() as db:
        assert db.query(PasswordReset).filter(PasswordReset.email == email).count() == 0


@pytest.mark.integration
def test_hash_code_is_email_bound(reset_client):
    """Code for one email must not confirm another account's reset."""
    email_a = "reset-a@test.local"
    email_b = "reset-b@test.local"
    register_basic_user(reset_client, email=email_a, name="A")
    reset_client.post("/auth/logout")
    register_basic_user(reset_client, email=email_b, name="B")
    reset_client.post("/auth/logout")

    code_a = _request(reset_client, email_a).json()["dev_code"]
    _request(reset_client, email_b)

    stolen = _confirm(reset_client, email_b, code_a, "ValidPass99")
    assert stolen.status_code == 400
