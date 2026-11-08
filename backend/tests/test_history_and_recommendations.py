import pytest
from fastapi.testclient import TestClient


def _get_auth_headers(client: TestClient) -> dict[str, str]:
    email = "rec_user@example.com"
    pwd = "password123"
    client.post("/api/auth/register", json={"email": email, "password": pwd, "display_name": "Rec Tester"})
    resp = client.post("/api/auth/token", json={"email": email, "password": pwd})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_history_and_continue_listening(client: TestClient):
    headers = _get_auth_headers(client)

    # 1. Record playback
    rec_resp = client.post(
        "/api/history",
        json={
            "service": "yandex",
            "service_id": "ym_1",
            "title": "Радиовышка",
            "artist": "Low Tower",
            "album": "Сигнал 404",
            "duration": 238,
        },
        headers=headers,
    )
    assert rec_resp.status_code == 201
    assert rec_resp.json()["album"] == "Сигнал 404"

    # 2. Get history
    hist_resp = client.get("/api/history", headers=headers)
    assert hist_resp.status_code == 200
    assert len(hist_resp.json()) == 1

    # 3. Get continue listening albums
    albums_resp = client.get("/api/history/albums", headers=headers)
    assert albums_resp.status_code == 200
    albums = albums_resp.json()
    assert len(albums) > 0
    assert any(a["title"] == "Сигнал 404" for a in albums)


def test_recommendations_and_wave_of_day(client: TestClient):
    # Recommendations endpoint
    rec_resp = client.get("/api/recommendations")
    assert rec_resp.status_code == 200
    tracks = rec_resp.json()
    assert len(tracks) > 0
    assert "title" in tracks[0]
    assert "sources" in tracks[0]

    # Wave of day endpoint
    wave_resp = client.get("/api/wave")
    assert wave_resp.status_code == 200
    wave = wave_resp.json()
    assert "date" in wave
    assert "title" in wave
    assert "description" in wave
    assert "trackCount" in wave
    assert "duration" in wave
    assert "tracks" in wave
    assert len(wave["tracks"]) > 0
