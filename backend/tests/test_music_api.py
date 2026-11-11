from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from services.music.dto import (
    AlbumDTO,
    ArtistDTO,
    PlaybackDTO,
    PlaybackKind,
    PlaylistDTO,
    SearchResultDTO,
    Service,
    TrackDTO,
)


def get_auth_headers(client: TestClient, email: str = "musicuser@example.com") -> dict[str, str]:
    client.post(
        "/api/auth/register",
        json={"email": email, "password": "password12345", "display_name": "Music User"},
    )
    login_res = client.post(
        "/api/auth/token",
        json={"email": email, "password": "password12345"},
    )
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_list_services(client: TestClient):
    resp = client.get("/api/services")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 5
    codes = [s["code"] for s in data]
    assert "ЯМ" in codes
    assert "YT" in codes
    assert "VK" in codes
    assert "SP" in codes
    assert "SC" in codes


def test_list_music_services(client: TestClient):
    resp = client.get("/api/music/services")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 5


def test_search_music(client: TestClient):
    mock_track = TrackDTO(
        service=Service.YANDEX,
        service_id="111:222",
        title="Test Song",
        artists=("Test Artist",),
        duration_ms=180000,
        playback=PlaybackDTO(kind=PlaybackKind.YANDEX_IFRAME, ref="111/222"),
        artwork_url="https://cover.test",
        sources=("ЯМ",),
    )
    mock_result = SearchResultDTO(query="Test", tracks=(mock_track,))

    with patch("app.api.music.aggregator.search", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = mock_result
        resp = client.get("/api/music/search?q=Test")

    assert resp.status_code == 200
    data = resp.json()
    assert data["query"] == "Test"
    assert len(data["tracks"]) == 1
    t = data["tracks"][0]
    assert t["title"] == "Test Song"
    assert t["artist"] == "Test Artist"
    assert t["duration"] == 180
    assert t["source"] == "ЯМ"
    assert t["sources"] == ["ЯМ"]
    assert t["playback"]["kind"] == "yandex_iframe"


def test_search_music_empty_query_fails(client: TestClient):
    resp = client.get("/api/music/search?q=")
    assert resp.status_code == 422


def test_get_track_success(client: TestClient):
    mock_track = TrackDTO(
        service=Service.YANDEX,
        service_id="111:222",
        title="Test Song",
        artists=("Test Artist",),
        duration_ms=180000,
        playback=PlaybackDTO(kind=PlaybackKind.YANDEX_IFRAME, ref="111/222"),
        artwork_url="https://cover.test",
        sources=("ЯМ",),
    )

    with patch("app.api.music.aggregator.get_track", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_track
        resp = client.get("/api/music/tracks/yandex/111:222")

    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Test Song"
    assert data["service"] == "yandex"
    assert data["service_id"] == "111:222"
    assert data["artist"] == "Test Artist"
    assert data["playback"]["ref"] == "111/222"


def test_get_track_not_found(client: TestClient):
    with patch("app.api.music.aggregator.get_track", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = None
        resp = client.get("/api/music/tracks/yandex/nonexistent")

    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_get_playback_info(client: TestClient):
    mock_track = TrackDTO(
        service=Service.YANDEX,
        service_id="111:222",
        title="Test Song",
        artists=("Test Artist",),
        playback=PlaybackDTO(kind=PlaybackKind.YANDEX_IFRAME, ref="111/222"),
        direct_audio_url="https://stream.test.mp3",
    )

    with patch("app.api.music.aggregator.get_track", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_track
        resp = client.get("/api/music/playback/yandex/111:222")

    assert resp.status_code == 200
    data = resp.json()
    assert data["kind"] == "yandex_iframe"
    assert data["ref"] == "111/222"
    assert data["direct_audio_url"] == "https://stream.test.mp3"


def test_get_playback_fallback(client: TestClient):
    with patch("app.api.music.aggregator.get_track", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = None
        resp = client.get("/api/music/playback/spotify/track123")

    assert resp.status_code == 200
    data = resp.json()
    assert data["kind"] == "spotify_sdk"
    assert data["ref"] == "spotify:track:track123"


def test_get_album_success(client: TestClient):
    mock_album = AlbumDTO(
        service=Service.YANDEX,
        service_id="222",
        title="Master of Puppets",
        artist="Metallica",
        year=1986,
        tracks_count=8,
        artwork_url="https://cover.test/album.jpg",
    )

    with patch("app.api.music.aggregator.get_album", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_album
        resp = client.get("/api/music/albums/yandex/222")

    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Master of Puppets"
    assert data["artist"] == "Metallica"
    assert data["year"] == 1986
    assert data["tracks_count"] == 8


def test_get_album_not_found(client: TestClient):
    with patch("app.api.music.aggregator.get_album", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = None
        resp = client.get("/api/music/albums/yandex/9999")

    assert resp.status_code == 404


def test_get_artist_success(client: TestClient):
    mock_artist = ArtistDTO(
        service=Service.YANDEX,
        service_id="333",
        name="Queen",
        genres=("rock",),
        artwork_url="https://cover.test/queen.jpg",
    )

    with patch("app.api.music.aggregator.get_artist", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_artist
        resp = client.get("/api/music/artists/yandex/333")

    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Queen"
    assert data["genres"] == ["rock"]


def test_get_artist_not_found(client: TestClient):
    with patch("app.api.music.aggregator.get_artist", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = None
        resp = client.get("/api/music/artists/yandex/9999")

    assert resp.status_code == 404


def test_get_playlist_success(client: TestClient):
    mock_pl = PlaylistDTO(
        service=Service.YANDEX,
        service_id="123:1",
        title="Night Drive",
        description="Vibes",
        tracks_count=10,
    )

    with patch("app.api.music.aggregator.get_playlist", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_pl
        resp = client.get("/api/music/playlists/yandex/123:1")

    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Night Drive"
    assert data["description"] == "Vibes"
    assert data["tracks_count"] == 10


def test_get_playlist_not_found(client: TestClient):
    with patch("app.api.music.aggregator.get_playlist", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = None
        resp = client.get("/api/music/playlists/yandex/999:1")

    assert resp.status_code == 404


def test_stream_track_redirect(client: TestClient):
    mock_track = TrackDTO(
        service=Service.YANDEX,
        service_id="111:222",
        title="Test Song",
        artists=("Test Artist",),
        direct_audio_url="https://storage.yandex.net/music/test.mp3",
    )

    with patch("app.api.music.aggregator.get_track", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_track
        resp = client.get("/api/music/tracks/yandex/111:222/stream?redirect=true", follow_redirects=False)

    assert resp.status_code == 307
    assert resp.headers["location"] == "https://storage.yandex.net/music/test.mp3"


def test_stream_track_not_available(client: TestClient):
    mock_track = TrackDTO(
        service=Service.YANDEX,
        service_id="111:222",
        title="Test Song",
        artists=("Test Artist",),
        direct_audio_url=None,
    )

    with patch("app.api.music.aggregator.get_track", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_track
        resp = client.get("/api/music/tracks/yandex/111:222/stream")

    assert resp.status_code == 404


# -------------------------------------------------------------------
# Service Account Linking & Personal Library Tests
# -------------------------------------------------------------------

def test_user_service_connections_flow(client: TestClient):
    headers = get_auth_headers(client, "connectuser@example.com")

    # 1. Initial connections
    resp = client.get("/api/services/connections", headers=headers)
    assert resp.status_code == 200
    conns = resp.json()
    assert len(conns) == 3
    for c in conns:
        assert c["connected"] is False

    # 2. Connect Yandex
    mock_ym_client = MagicMock()
    mock_ym_client.me.account.full_name = "Leo Test"
    mock_ym_client.me.account.login = "leo_login"
    mock_ym_client.me.account.uid = 123456

    with patch("yandex_music.Client") as mock_client_cls:
        mock_client_cls.return_value.init.return_value = mock_ym_client
        connect_res = client.post(
            "/api/services/yandex/connect",
            json={"token": "test_yandex_token_123"},
            headers=headers,
        )

    assert connect_res.status_code == 200
    yandex_data = connect_res.json()
    assert yandex_data["service"] == "yandex"
    assert yandex_data["connected"] is True
    assert yandex_data["account_name"] == "Leo Test"

    # 3. Connect YouTube
    with patch("app.api.services.YTMusic") as mock_yt_cls:
        mock_yt = MagicMock()
        mock_yt.get_library_playlists.return_value = [{"title": "My YT Playlist"}]
        mock_yt_cls.return_value = mock_yt
        yt_connect_res = client.post(
            "/api/services/youtube/connect",
            json={"token": "fake_yt_oauth_token"},
            headers=headers,
        )

    assert yt_connect_res.status_code == 200
    yt_data = yt_connect_res.json()
    assert yt_data["service"] == "youtube"
    assert yt_data["connected"] is True

    # 4. Check connections again
    resp2 = client.get("/api/services/connections", headers=headers)
    conns2 = {c["service"]: c for c in resp2.json()}
    assert conns2["yandex"]["connected"] is True
    assert conns2["youtube"]["connected"] is True
    assert conns2["vk"]["connected"] is False

    # 5. Toggle service
    toggle_res = client.put(
        "/api/services/yandex/toggle",
        json={"is_active": False},
        headers=headers,
    )
    assert toggle_res.status_code == 200
    assert toggle_res.json()["is_active"] is False

    # 6. Disconnect service
    disconn_res = client.delete("/api/services/yandex/disconnect", headers=headers)
    assert disconn_res.status_code == 200
    assert disconn_res.json()["connected"] is False


def test_user_personal_playlists_and_favorites(client: TestClient):
    headers = get_auth_headers(client, "personaluser@example.com")

    # Connect Yandex
    mock_ym_client = MagicMock()
    mock_ym_client.me.account.full_name = "Personal User"
    mock_ym_client.me.account.login = "personal_login"
    mock_ym_client.me.account.uid = 777

    with patch("yandex_music.Client") as mock_client_cls:
        mock_client_cls.return_value.init.return_value = mock_ym_client
        client.post(
            "/api/services/yandex/connect",
            json={"token": "valid_token"},
            headers=headers,
        )

    mock_playlist = PlaylistDTO(
        service=Service.YANDEX,
        service_id="777:1",
        title="Personal Favorites",
    )
    mock_track = TrackDTO(
        service=Service.YANDEX,
        service_id="999:111",
        title="Loved Song",
        artists=("Loved Artist",),
    )

    with patch("app.api.music.aggregator.get_user_playlists", new_callable=AsyncMock) as mock_get_pls:
        mock_get_pls.return_value = [mock_playlist]
        pls_resp = client.get("/api/music/me/playlists", headers=headers)

    assert pls_resp.status_code == 200
    pls_data = pls_resp.json()
    assert len(pls_data) == 1
    assert pls_data[0]["name"] == "Personal Favorites"

    with patch("app.api.music.aggregator.get_user_favorites", new_callable=AsyncMock) as mock_get_favs:
        mock_get_favs.return_value = [mock_track]
        favs_resp = client.get("/api/music/me/favorites", headers=headers)

    assert favs_resp.status_code == 200
    favs_data = favs_resp.json()
    assert len(favs_data) == 1
    assert favs_data[0]["title"] == "Loved Song"
    assert favs_data[0]["liked"] is True


def test_youtube_device_code_endpoint(client: TestClient):
    mock_code_data = {
        "device_code": "dev123",
        "user_code": "ABCD-EFGH",
        "verification_url": "https://www.google.com/device",
        "expires_in": 1800,
        "interval": 5,
    }

    with patch("app.api.services.OAuthCredentials") as mock_creds_cls:
        mock_creds = MagicMock()
        mock_creds.get_code.return_value = mock_code_data
        mock_creds_cls.return_value = mock_creds

        resp = client.post(
            "/api/services/youtube/oauth/device-code?client_id=test_cid&client_secret=test_sec"
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["user_code"] == "ABCD-EFGH"
    assert data["verification_url"] == "https://www.google.com/device"


def test_yandex_stream_signed_url_flow(client: TestClient):
    # 1. Register and login
    email = "yandex_stream_user@example.com"
    password = "SecurePassword123!"
    client.post("/api/auth/register", json={"email": email, "password": password, "display_name": "Streamer"})
    token_resp = client.post("/api/auth/token", json={"email": email, "password": password})
    token = token_resp.json()["access"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Get track metadata as authenticated user
    mock_track = TrackDTO(
        service=Service.YANDEX,
        service_id="999:888",
        title="Yandex Stream Song",
        artists=("Stream Artist",),
        direct_audio_url="https://storage.yandex.net/music/stream_song.mp3",
    )
    with patch("app.api.music.aggregator.get_track", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_track
        resp = client.get("/api/music/tracks/yandex/999:888", headers=headers)

    assert resp.status_code == 200
    data = resp.json()
    stream_url = data["direct_audio_url"]
    assert "/api/music/tracks/yandex/999:888/stream?u=" in stream_url
    assert "&sig=" in stream_url

    # 3. Stream request with signed query params without Authorization header
    with patch("app.api.music.aggregator.get_track", new_callable=AsyncMock) as mock_stream_get:
        mock_stream_get.return_value = mock_track
        stream_resp = client.get(f"{stream_url}&redirect=true", follow_redirects=False)

    assert stream_resp.status_code == 307
    assert stream_resp.headers["location"] == "https://storage.yandex.net/music/stream_song.mp3"

