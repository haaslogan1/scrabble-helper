"""Single-session enforcement tests."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from tests.qa_gameplay import DEFAULT_PASSWORD, register_basic_user


def _make_client(monkeypatch) -> TestClient:
    monkeypatch.setattr(settings, "dev_auth_bypass", False)
    monkeypatch.setattr(settings, "local_auth_enabled", True)
    monkeypatch.setattr(settings, "email_verification_enabled", True)
    monkeypatch.setattr(settings, "email_verification_dev_expose_code", True)
    return TestClient(app)


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
            assert client2.get("/auth/me").status_code == 200

            superseded = client1.get("/auth/me")
            assert superseded.status_code == 401
            detail = superseded.json()["detail"]
            assert detail["code"] == "session_superseded"

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
def test_logout_does_not_invalidate_other_clients(monkeypatch):
    email = f"logout-{uuid.uuid4().hex[:8]}@test.local"
    with _make_client(monkeypatch) as client1:
        register_basic_user(client1, email=email)

        with _make_client(monkeypatch) as client2:
            login2 = client2.post(
                "/auth/login",
                json={"email": email, "password": DEFAULT_PASSWORD},
            )
            assert login2.status_code == 200
            assert client2.get("/auth/me").status_code == 200

            client1.post("/auth/logout")
            assert client2.get("/auth/me").status_code == 200
