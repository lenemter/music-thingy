import pytest
from fastapi.testclient import TestClient


def _get_auth_headers(client: TestClient) -> dict[str, str]:
    email = "service_test@example.com"
    pwd = "password123"
    client.post("/api/auth/register", json={"email": email, "password": pwd, "display_name": "Service User"})
    resp = client.post("/api/auth/token", json={"email": email, "password": pwd})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_list_services_unauthenticated(client: TestClient):
    resp = client.get("/api/services")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 4
    codes = [s["code"] for s in data]
    assert "ЯМ" in codes
    assert "SP" in codes
    assert "SC" in codes
    assert "YT" in codes


def test_update_service_preferences(client: TestClient):
    headers = _get_auth_headers(client)

    # Disable all except Yandex and Spotify
    payload = {"enabled_services": ["ям", "spotify"]}
    resp = client.put("/api/services/preferences", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    ym = next(s for s in data if s["code"] == "ЯМ")
    sp = next(s for s in data if s["code"] == "SP")
    sc = next(s for s in data if s["code"] == "SC")
    yt = next(s for s in data if s["code"] == "YT")

    assert ym["online"] is True
    assert sp["online"] is True
    assert sc["online"] is False
    assert yt["online"] is False
