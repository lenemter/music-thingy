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


def test_list_services(client: TestClient):
    resp = client.get("/api/services")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 4
    codes = [s["code"] for s in data]
    assert "ЯМ" in codes
    assert "SP" in codes
    assert "SC" in codes
    assert "YT" in codes


def test_list_music_services(client: TestClient):
    resp = client.get("/api/music/services")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 4


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
