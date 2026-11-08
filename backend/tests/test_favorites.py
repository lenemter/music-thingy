import pytest
from fastapi.testclient import TestClient


def _get_auth_headers(client: TestClient) -> dict[str, str]:
    email = "favorite_user@example.com"
    pwd = "password123"
    client.post("/api/auth/register", json={"email": email, "password": pwd, "display_name": "Favorite Tester"})
    resp = client.post("/api/auth/token", json={"email": email, "password": pwd})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_favorites_tracks_and_albums(client: TestClient):
    headers = _get_auth_headers(client)

    # 1. Add favorite track
    resp = client.post(
        "/api/favorites/tracks",
        json={
            "service": "yandex",
            "service_id": "ym_101",
            "title": "Радиовышка",
            "artist": "Low Tower",
            "duration": 238,
            "sources": ["ЯМ", "SP"],
        },
        headers=headers,
    )
    assert resp.status_code == 201
    track = resp.json()
    assert track["liked"] is True
    assert track["title"] == "Радиовышка"

    # 2. Check check endpoint
    check_resp = client.get("/api/favorites/check", headers=headers)
    assert check_resp.status_code == 200
    assert "yandex:ym_101" in check_resp.json()["liked_keys"]

    # 3. List favorite tracks
    list_resp = client.get("/api/favorites/tracks", headers=headers)
    assert list_resp.status_code == 200
    fav_tracks = list_resp.json()
    assert len(fav_tracks) == 1
    assert fav_tracks[0]["service_id"] == "ym_101"

    # 4. Remove favorite track
    del_resp = client.delete("/api/favorites/tracks/yandex/ym_101", headers=headers)
    assert del_resp.status_code == 204

    # Verify empty
    assert len(client.get("/api/favorites/tracks", headers=headers).json()) == 0

    # 5. Favorite album lifecycle
    alb_resp = client.post(
        "/api/favorites/albums",
        json={
            "service": "spotify",
            "service_id": "alb_42",
            "title": "Солнцеворот",
            "subtitle": "Орбита 9 · альбом",
        },
        headers=headers,
    )
    assert alb_resp.status_code == 201
    assert alb_resp.json()["title"] == "Солнцеворот"

    albs_list = client.get("/api/favorites/albums", headers=headers).json()
    assert len(albs_list) == 1

    client.delete("/api/favorites/albums/spotify/alb_42", headers=headers)
    assert len(client.get("/api/favorites/albums", headers=headers).json()) == 0
