import pytest
from fastapi.testclient import TestClient


def _get_auth_headers(client: TestClient) -> dict[str, str]:
    email = "playlist_user@example.com"
    pwd = "password123"
    client.post("/api/auth/register", json={"email": email, "password": pwd, "display_name": "Playlist Tester"})
    resp = client.post("/api/auth/token", json={"email": email, "password": pwd})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_playlist_lifecycle(client: TestClient):
    headers = _get_auth_headers(client)

    # 1. Create playlist
    create_resp = client.post(
        "/api/playlists",
        json={"name": "Ночные поездки", "description": "Для дороги", "is_public": True},
        headers=headers,
    )
    assert create_resp.status_code == 201
    p_data = create_resp.json()
    p_id = p_data["id"]
    assert p_data["name"] == "Ночные поездки"
    assert p_data["tracks_count"] == 0

    # 2. Add track to playlist
    add_resp = client.post(
        f"/api/playlists/{p_id}/tracks",
        json={
            "service": "yandex",
            "service_id": "12345",
            "title": "Радиовышка",
            "artist": "Low Tower",
            "duration": 238,
            "playback_kind": "yandex_iframe",
            "playback_ref": "12345/678",
        },
        headers=headers,
    )
    assert add_resp.status_code == 201
    t1_id = add_resp.json()["id"]

    # Add second track
    add2_resp = client.post(
        f"/api/playlists/{p_id}/tracks",
        json={
            "service": "spotify",
            "service_id": "sp_999",
            "title": "Солнцеворот",
            "artist": "Орбита 9",
            "duration": 252,
        },
        headers=headers,
    )
    assert add2_resp.status_code == 201
    t2_id = add2_resp.json()["id"]

    # 3. Get playlist with tracks
    get_resp = client.get(f"/api/playlists/{p_id}", headers=headers)
    assert get_resp.status_code == 200
    p_full = get_resp.json()
    assert p_full["tracks_count"] == 2
    assert len(p_full["tracks"]) == 2
    assert p_full["tracks"][0]["title"] == "Радиовышка"

    # 4. Reorder tracks
    reorder_resp = client.put(
        f"/api/playlists/{p_id}/reorder",
        json={"track_ids": [t2_id, t1_id]},
        headers=headers,
    )
    assert reorder_resp.status_code == 200
    assert reorder_resp.json()["tracks"][0]["id"] == t2_id

    # 5. Remove track
    del_track_resp = client.delete(f"/api/playlists/{p_id}/tracks/{t1_id}", headers=headers)
    assert del_track_resp.status_code == 204

    # 6. Delete playlist
    del_resp = client.delete(f"/api/playlists/{p_id}", headers=headers)
    assert del_resp.status_code == 204

    # Verify not found
    assert client.get(f"/api/playlists/{p_id}", headers=headers).status_code == 404
