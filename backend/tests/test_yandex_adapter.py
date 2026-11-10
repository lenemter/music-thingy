from unittest.mock import MagicMock, patch
import pytest

from services.music.base import AdapterError
from services.music.dto import ErrorKind, SearchType, Service
from services.music.yandex import (
    YandexMusicAdapter,
    _cover_url,
    _to_album,
    _to_artist,
    _to_playlist,
    _to_track,
    _translate_errors,
)
from yandex_music.exceptions import (
    BadRequestError,
    NotFoundError,
    TimedOutError,
    UnauthorizedError,
    YandexMusicError,
)


def test_cover_url():
    entity = MagicMock()
    entity.cover_uri = "avatars.yandex.net/get-music-content/123/%%"
    assert _cover_url(entity, "300x300") == "https://avatars.yandex.net/get-music-content/123/300x300"

    entity.cover_uri = None
    mock_cover = MagicMock()
    mock_cover.uri = "https://cdn.example.com/%%"
    entity.cover = mock_cover
    assert _cover_url(entity) == "https://cdn.example.com/400x400"

    entity.cover = None
    entity.og_image = None
    assert _cover_url(entity) is None


def test_translate_errors():
    with pytest.raises(AdapterError) as exc_info:
        with _translate_errors():
            raise UnauthorizedError("Invalid token")
    assert exc_info.value.kind == ErrorKind.AUTH_FAILED
    assert exc_info.value.status_code == 401

    with pytest.raises(AdapterError) as exc_info:
        with _translate_errors():
            raise TimedOutError()
    assert exc_info.value.kind == ErrorKind.TIMEOUT

    with pytest.raises(AdapterError) as exc_info:
        with _translate_errors():
            raise NotFoundError("Track not found")
    assert exc_info.value.kind == ErrorKind.UNAVAILABLE
    assert exc_info.value.status_code == 404

    with pytest.raises(AdapterError) as exc_info:
        with _translate_errors():
            raise BadRequestError("Bad request")
    assert exc_info.value.kind == ErrorKind.UNKNOWN

    with pytest.raises(AdapterError) as exc_info:
        with _translate_errors():
            raise YandexMusicError("Generic error")
    assert exc_info.value.kind == ErrorKind.UNKNOWN


def test_to_track():
    mock_artist = MagicMock()
    mock_artist.id = 10
    mock_artist.name = "Queen"

    mock_album = MagicMock()
    mock_album.id = 20
    mock_album.title = "A Night at the Opera"

    mock_track = MagicMock()
    mock_track.id = 30
    mock_track.title = "Bohemian Rhapsody"
    mock_track.version = None
    mock_track.available = True
    mock_track.duration_ms = 354000
    mock_track.artists = [mock_artist]
    mock_track.albums = [mock_album]
    mock_track.cover_uri = "avatars.yandex.net/%%"
    mock_track.cover = None
    mock_track.og_image = None

    dto = _to_track(mock_track, direct_audio_url="https://audio.url")
    assert dto is not None
    assert dto.service == Service.YANDEX
    assert dto.service_id == "30:20"
    assert dto.title == "Bohemian Rhapsody"
    assert dto.artists == ("Queen",)
    assert dto.artist_ids == ("10",)
    assert dto.is_playable is True
    assert dto.playback is not None
    assert dto.playback.ref == "30/20"
    assert dto.direct_audio_url == "https://audio.url"
    assert dto.sources == ("ЯМ",)


def test_to_artist():
    mock_artist = MagicMock()
    mock_artist.id = 10
    mock_artist.name = "Queen"
    mock_artist.genres = ["rock"]
    mock_artist.cover_uri = "avatars.yandex.net/%%"
    mock_artist.cover = None
    mock_artist.og_image = None

    dto = _to_artist(mock_artist)
    assert dto is not None
    assert dto.service == Service.YANDEX
    assert dto.service_id == "10"
    assert dto.name == "Queen"
    assert dto.genres == ("rock",)


def test_to_album():
    mock_artist = MagicMock()
    mock_artist.id = 10
    mock_artist.name = "Queen"

    mock_album = MagicMock()
    mock_album.id = 20
    mock_album.title = "A Night at the Opera"
    mock_album.artists = [mock_artist]
    mock_album.year = 1975
    mock_album.track_count = 12
    mock_album.cover_uri = "avatars.yandex.net/%%"
    mock_album.cover = None
    mock_album.og_image = None

    dto = _to_album(mock_album)
    assert dto is not None
    assert dto.service == Service.YANDEX
    assert dto.service_id == "20"
    assert dto.title == "A Night at the Opera"
    assert dto.artist == "Queen"
    assert dto.year == 1975
    assert dto.tracks_count == 12


def test_to_playlist():
    mock_owner = MagicMock()
    mock_owner.name = "Leo"
    mock_owner.login = "leo_user"

    mock_playlist = MagicMock()
    mock_playlist.uid = 12345
    mock_playlist.kind = 3
    mock_playlist.title = "Rock Classics"
    mock_playlist.description = "Best rock songs"
    mock_playlist.track_count = 50
    mock_playlist.owner = mock_owner
    mock_playlist.cover_uri = "avatars.yandex.net/%%"
    mock_playlist.cover = None
    mock_playlist.og_image = None

    dto = _to_playlist(mock_playlist)
    assert dto is not None
    assert dto.service == Service.YANDEX
    assert dto.service_id == "12345:3"
    assert dto.title == "Rock Classics"
    assert dto.tracks_count == 50


@patch("services.music.yandex.Client")
def test_adapter_search(mock_client_cls):
    mock_client = MagicMock()
    mock_client_cls.return_value.init.return_value = mock_client

    mock_artist = MagicMock()
    mock_artist.id = 10
    mock_artist.name = "Singer"

    mock_album = MagicMock()
    mock_album.id = 20
    mock_album.title = "Album"

    mock_track = MagicMock()
    mock_track.id = 1
    mock_track.title = "Song"
    mock_track.version = None
    mock_track.available = True
    mock_track.artists = [mock_artist]
    mock_track.albums = [mock_album]
    mock_track.cover_uri = None
    mock_track.cover = None
    mock_track.og_image = None
    mock_track.duration_ms = 120000

    mock_search_res = MagicMock()
    mock_search_res.tracks.results = [mock_track]
    mock_search_res.artists.results = []
    mock_search_res.albums.results = []
    mock_search_res.playlists.results = []
    mock_client.search.return_value = mock_search_res

    adapter = YandexMusicAdapter()
    result = adapter.search("Song", types=frozenset({SearchType.TRACK}), limit=5)

    assert result.query == "Song"
    assert len(result.tracks) == 1
    assert result.tracks[0].title == "Song"
    assert result.tracks[0].artists == ("Singer",)


@patch("services.music.yandex.Client")
def test_adapter_get_track_not_found(mock_client_cls):
    mock_client = MagicMock()
    mock_client_cls.return_value.init.return_value = mock_client
    mock_client.tracks.return_value = []

    adapter = YandexMusicAdapter()
    assert adapter.get_track("999999") is None


@patch("services.music.yandex.Client")
def test_adapter_get_album(mock_client_cls):
    mock_client = MagicMock()
    mock_client_cls.return_value.init.return_value = mock_client

    mock_artist = MagicMock()
    mock_artist.id = 10
    mock_artist.name = "Singer"

    mock_track = MagicMock()
    mock_track.id = 1
    mock_track.title = "Album Track"
    mock_track.version = None
    mock_track.available = True
    mock_track.artists = [mock_artist]
    mock_track.albums = []
    mock_track.cover_uri = None
    mock_track.cover = None
    mock_track.og_image = None
    mock_track.duration_ms = 180000

    mock_album = MagicMock()
    mock_album.id = 55
    mock_album.title = "My Album"
    mock_album.artists = [mock_artist]
    mock_album.year = 2023
    mock_album.track_count = 1
    mock_album.cover_uri = None
    mock_album.cover = None
    mock_album.og_image = None
    mock_album.volumes = [[mock_track]]
    mock_client.albums_with_tracks.return_value = mock_album

    adapter = YandexMusicAdapter()
    alb = adapter.get_album("55")
    assert alb is not None
    assert alb.title == "My Album"
    assert alb.tracks is not None
    assert len(alb.tracks) == 1
    assert alb.tracks[0].title == "Album Track"
