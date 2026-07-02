import pytest

from app.config import settings


@pytest.mark.unit
def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.unit
def test_health_db(client):
    response = client.get("/health", params={"db": True})
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "db": "ok"}


@pytest.mark.integration
def test_auth_me(client):
    response = client.get("/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert "email" in data
    assert "name" in data


@pytest.mark.integration
def test_auth_config_public(client):
    response = client.get("/auth/config")
    assert response.status_code == 200
    data = response.json()
    assert "google_login_enabled" in data
    assert "dev_login_enabled" in data
    assert "local_auth_enabled" in data


@pytest.mark.integration
def test_api_requires_auth_when_bypass_disabled(client, monkeypatch):
    monkeypatch.setattr(settings, "dev_auth_bypass", False)
    response = client.get("/api/home")
    assert response.status_code == 401


@pytest.mark.integration
def test_auth_me_requires_session_when_bypass_disabled(client, monkeypatch):
    monkeypatch.setattr(settings, "dev_auth_bypass", False)
    response = client.get("/auth/me")
    assert response.status_code == 401
