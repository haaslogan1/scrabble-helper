import pytest


@pytest.mark.integration
def test_create_and_list_players(client):
    create = client.post("/api/players", json={"name": "Alice"})
    assert create.status_code == 200
    assert create.json()["name"] == "Alice"

    listing = client.get("/api/players")
    assert listing.status_code == 200
    names = [p["name"] for p in listing.json()]
    assert "Alice" in names


@pytest.mark.integration
def test_player_names_unique_per_user(client):
    client.post("/api/players", json={"name": "Bob"})
    again = client.post("/api/players", json={"name": "Bob"})
    assert again.status_code == 200
    assert again.json()["name"] == "Bob"
