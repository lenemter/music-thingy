from fastapi.testclient import TestClient


def _auth_headers(client: TestClient, email: str = "playlist_user@example.com") -> dict[str, str]:
    reg = client.post(
        "/api/auth/register",
        json={"email": email, "password": "StrongPassword123!", "full_name": "Playlist User"},
    )
    assert reg.status_code in (200, 201), reg.text
    tok = client.post(
        "/api/auth/token",
        data={"username": email, "password": "StrongPassword123!"},
    )
    assert tok.status_code == 200, tok.text
    access_token = tok.json()["access_token"]
    return {"Authorization": f"Bearer {access_token}"}


def test_playlists_require_auth(client: TestClient):
    res = client.get("/api/playlists")
    assert res.status_code == 401


def test_create_list_rename_delete_playlist(client: TestClient):
    headers = _auth_headers(client)

    # Create with 5 tracks (covers should be capped at 4, duplicate track ignored)
    tracks = [
        {
            "service": "vk",
            "service_id": f"100_{i}",
            "title": f"Track {i}",
            "artist": f"Artist {i}",
            "cover": f"https://example.com/c{i}.jpg",
            "duration": 120 + i,
        }
        for i in range(1, 6)
    ]
    tracks.append({"service": "vk", "service_id": "100_1", "title": "Dup"})

    create_res = client.post(
        "/api/playlists",
        headers=headers,
        json={"name": "  Ночные поездки  ", "tracks": tracks},
    )
    assert create_res.status_code == 201, create_res.text
    pl = create_res.json()
    assert pl["name"] == "Ночные поездки"
    assert pl["tracks_count"] == 5
    assert pl["duration"] == sum(120 + i for i in range(1, 6))
    assert pl["covers"] == [f"https://example.com/c{i}.jpg" for i in range(1, 5)]

    # List playlists
    list_res = client.get("/api/playlists", headers=headers)
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1
    assert list_res.json()[0]["id"] == pl["id"]

    # Rename playlist
    rename_res = client.patch(
        f"/api/playlists/{pl['id']}",
        headers=headers,
        json={"name": "Дневные поездки"},
    )
    assert rename_res.status_code == 200
    assert rename_res.json()["name"] == "Дневные поездки"

    # Delete playlist
    del_res = client.delete(f"/api/playlists/{pl['id']}", headers=headers)
    assert del_res.status_code == 204
    assert client.get("/api/playlists", headers=headers).json() == []


def test_playlist_name_uniqueness_and_reserved(client: TestClient):
    headers = _auth_headers(client, "uniq@example.com")

    # Reserved name on create
    res_reserved = client.post(
        "/api/playlists",
        headers=headers,
        json={"name": "  понравившиеся "},
    )
    assert res_reserved.status_code == 409

    # Create "Рок"
    r1 = client.post("/api/playlists", headers=headers, json={"name": "Рок"})
    assert r1.status_code == 201
    pl1_id = r1.json()["id"]

    # Duplicate case-insensitive + trimmed
    r2 = client.post("/api/playlists", headers=headers, json={"name": "  рок  "})
    assert r2.status_code == 409

    # Create another playlist and try renaming to duplicate or reserved
    r3 = client.post("/api/playlists", headers=headers, json={"name": "Джаз"})
    assert r3.status_code == 201
    pl2_id = r3.json()["id"]

    assert client.patch(f"/api/playlists/{pl2_id}", headers=headers, json={"name": " РОК "}).status_code == 409
    assert client.patch(f"/api/playlists/{pl2_id}", headers=headers, json={"name": "Понравившиеся"}).status_code == 409
    # Renaming to same name (different case) on self is allowed
    r_self = client.patch(f"/api/playlists/{pl1_id}", headers=headers, json={"name": "рок"})
    assert r_self.status_code == 200
    assert r_self.json()["name"] == "рок"

    # Empty name rejected
    assert client.post("/api/playlists", headers=headers, json={"name": "   "}).status_code == 400


def test_playlist_tracks_add_dedup_pagination_liked_and_remove(client: TestClient):
    headers = _auth_headers(client, "tracks@example.com")
    pl = client.post("/api/playlists", headers=headers, json={"name": "Микс"}).json()
    pl_id = pl["id"]

    # Add two tracks
    r1 = client.post(
        f"/api/playlists/{pl_id}/tracks",
        headers=headers,
        json={
            "service": "youtube",
            "service_id": "yt1",
            "title": "First",
            "artist": "Artist A",
            "cover": "https://img.test/1.jpg",
            "duration": 200,
        },
    )
    assert r1.status_code == 200
    assert r1.json()["tracks_count"] == 1

    # Idempotent duplicate add
    r1_dup = client.post(
        f"/api/playlists/{pl_id}/tracks",
        headers=headers,
        json={"service": "YOUTUBE", "service_id": "yt1", "title": "Changed"},
    )
    assert r1_dup.status_code == 200
    assert r1_dup.json()["tracks_count"] == 1

    r2 = client.post(
        f"/api/playlists/{pl_id}/tracks",
        headers=headers,
        json={
            "service": "yandex",
            "service_id": "ym2",
            "title": "Second",
            "artist": "Artist B",
            "duration": 150,
        },
    )
    assert r2.status_code == 200
    assert r2.json()["tracks_count"] == 2
    assert r2.json()["duration"] == 350

    # Like second track
    like_res = client.put(
        "/api/music/tracks/yandex/ym2/like",
        headers=headers,
        json={"title": "Second", "artist": "Artist B", "duration": 150},
    )
    assert like_res.status_code == 200

    # Get tracks in order + pagination
    page1 = client.get(f"/api/playlists/{pl_id}/tracks?offset=0&limit=1", headers=headers)
    assert page1.status_code == 200
    assert len(page1.json()) == 1
    assert page1.json()[0]["service_id"] == "yt1"
    assert page1.json()[0]["liked"] is False

    page2 = client.get(f"/api/playlists/{pl_id}/tracks?offset=1&limit=10", headers=headers)
    assert page2.status_code == 200
    assert len(page2.json()) == 1
    assert page2.json()[0]["service_id"] == "ym2"
    assert page2.json()[0]["liked"] is True

    # Remove first track
    rem = client.delete(f"/api/playlists/{pl_id}/tracks/youtube/yt1", headers=headers)
    assert rem.status_code == 200
    assert rem.json()["tracks_count"] == 1
    assert rem.json()["duration"] == 150
    assert rem.json()["covers"] == []


def test_playlist_ownership_isolation(client: TestClient):
    h1 = _auth_headers(client, "owner1@example.com")
    h2 = _auth_headers(client, "owner2@example.com")

    pl = client.post("/api/playlists", headers=h1, json={"name": "Личный"}).json()
    pl_id = pl["id"]

    # Second user can create playlist with the same name
    assert client.post("/api/playlists", headers=h2, json={"name": "Личный"}).status_code == 201

    # Second user cannot access/modify/delete first user's playlist
    assert client.patch(f"/api/playlists/{pl_id}", headers=h2, json={"name": "Hack"}).status_code == 404
    assert client.delete(f"/api/playlists/{pl_id}", headers=h2).status_code == 404
    assert client.get(f"/api/playlists/{pl_id}/tracks", headers=h2).status_code == 404
    assert (
        client.post(
            f"/api/playlists/{pl_id}/tracks",
            headers=h2,
            json={"service": "vk", "service_id": "1"},
        ).status_code
        == 404
    )
    assert client.delete(f"/api/playlists/{pl_id}/tracks/vk/1", headers=h2).status_code == 404
