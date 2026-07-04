import uuid

import pytest

from tests.qa_gameplay import (
    DEFAULT_PASSWORD,
    login_basic_user,
    play_turn,
    register_basic_user,
    setup_and_begin_game,
)


@pytest.mark.integration
def test_register_and_login(basic_client):
    email = "newbasic@test.local"
    user = register_basic_user(basic_client, email=email, name="New Basic")
    assert user["email"] == email

    basic_client.post("/auth/logout")
    logged_in = login_basic_user(basic_client, email=email)
    assert logged_in["email"] == email


@pytest.mark.integration
def test_login_wrong_password(basic_client):
    register_basic_user(basic_client, email="wrongpw@test.local")
    basic_client.post("/auth/logout")
    res = basic_client.post(
        "/auth/login",
        json={"email": "wrongpw@test.local", "password": "WrongPass99"},
    )
    assert res.status_code == 401


@pytest.mark.integration
def test_duplicate_register(basic_client):
    register_basic_user(basic_client, email="dup@test.local")
    res = basic_client.post(
        "/auth/register/send-code",
        json={"email": "dup@test.local", "password": DEFAULT_PASSWORD, "name": "Dup"},
    )
    assert res.status_code == 409


@pytest.mark.integration
def test_weak_password_rejected(basic_client):
    res = basic_client.post(
        "/auth/register/send-code",
        json={"email": "weak@test.local", "password": "short", "name": "Weak"},
    )
    assert res.status_code == 400


@pytest.mark.integration
def test_invalid_email_rejected(basic_client):
    res = basic_client.post(
        "/auth/register/send-code",
        json={"email": "not-an-email", "password": DEFAULT_PASSWORD, "name": "Bad"},
    )
    assert res.status_code == 400
    assert "valid email" in res.json()["detail"].lower()


@pytest.mark.integration
def test_wrong_verification_code(basic_client):
    email = "verify-fail@test.local"
    send = basic_client.post(
        "/auth/register/send-code",
        json={"email": email, "password": DEFAULT_PASSWORD, "name": "Verify"},
    )
    assert send.status_code == 200
    verify = basic_client.post(
        "/auth/register/verify",
        json={"email": email, "code": "000000"},
    )
    assert verify.status_code == 400
    assert "incorrect" in verify.json()["detail"].lower()


@pytest.mark.integration
def test_non_admin_cannot_access_admin(auth_client):
    res = auth_client.get("/api/admin/users")
    assert res.status_code == 403


@pytest.mark.integration
def test_admin_lists_and_deletes_games(admin_client, basic_client):
    victim_email = f"victim-{uuid.uuid4().hex[:8]}@test.local"
    register_basic_user(basic_client, email=victim_email)
    game_id = setup_and_begin_game(basic_client, ["A", "B"])
    play_turn(basic_client, game_id, 15)

    games = admin_client.get("/api/admin/games", params={"owner_email": victim_email})
    assert games.status_code == 200
    assert any(g["id"] == game_id for g in games.json())

    deleted = admin_client.delete(f"/api/admin/users/by-email/{victim_email}/games")
    assert deleted.status_code == 200
    assert deleted.json()["deleted_count"] >= 1

    games_after = admin_client.get("/api/admin/games", params={"owner_email": victim_email})
    assert games_after.json() == []


@pytest.mark.integration
def test_invalid_points_do_not_advance(auth_client):
    game_id = setup_and_begin_game(auth_client, ["P1", "P2"])
    bad = play_turn(auth_client, game_id, 0)
    assert bad.status_code == 400
    state = auth_client.get(f"/api/games/{game_id}/state")
    assert state.json()["current_player"] == "QA User"

    good = play_turn(auth_client, game_id, 12)
    assert good.status_code == 200
    assert good.json()["current_player"] == "P1"
    scores = {s["name"]: s["total_score"] for s in good.json()["standings"]}
    assert scores["QA User"] == 12
