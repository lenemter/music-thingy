import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from curl_cffi.requests.exceptions import RequestException, Timeout

from app.config import settings
from services.music.base import AdapterError
from services.music.dto import ErrorKind, SearchType, Service
from services.music.vk import (
    VkMusicAdapter,
    _audio_ref,
    _none_if_empty,
    _to_playlist,
    _to_track,
    _translate_errors,
)


def make_song(**kw):
    data = dict(
        track_id=111, owner_id=222, title="Song", artist="Artist",
        url="https://cdn.test/a.mp3", duration=180,
    )
    data.update(kw)
    return SimpleNamespace(**data)


def make_playlist(**kw):
    data = dict(
        owner_id=1, playlist_id=2, title="My PL", description="desc",
        count=1, photo="https://cdn.test/p.jpg", access_key=None,
    )
    data.update(kw)
    return SimpleNamespace(**data)


@pytest.fixture
def vk():
    """Подменяет vkpymusic.Service и отдаёт мок клиента VK."""
    with patch("services.music.vk.VkService") as service_cls:
        yield service_cls.return_value


@pytest.fixture
def adapter(vk):
    return VkMusicAdapter("token", "user-agent", min_interval=0)


# ---------- вспомогательные функции ----------

def test_none_if_empty():
    assert _none_if_empty(None) is None
    assert _none_if_empty("   ") is None
    assert _none_if_empty(" x ") == "x"
    assert _none_if_empty(0) == "0"


def test_audio_ref():
    assert _audio_ref(1, 2) == "1_2"
    assert _audio_ref(-1, 2, "key") == "-1_2_key"


def test_translate_errors_maps_exceptions():
    with pytest.raises(AdapterError) as exc:
        with _translate_errors():
            raise Timeout("slow")
    assert exc.value.kind == ErrorKind.TIMEOUT

    with pytest.raises(AdapterError) as exc:
        with _translate_errors():
            raise RequestException("net")
    assert exc.value.kind == ErrorKind.UNAVAILABLE

    with pytest.raises(AdapterError) as exc:
        with _translate_errors():
            raise OSError("disk")
    assert exc.value.kind == ErrorKind.UNAVAILABLE

    with pytest.raises(AdapterError) as exc:
        with _translate_errors():
            raise KeyError("x")
    assert exc.value.kind == ErrorKind.UNKNOWN


def test_translate_errors_passes_adapter_error_through():
    original = AdapterError(ErrorKind.AUTH_FAILED, "no", 401)
    with pytest.raises(AdapterError) as exc:
        with _translate_errors():
            raise original
    assert exc.value is original


# ---------- конвертеры ----------

def test_to_track_basic():
    dto = _to_track(make_song())
    assert dto is not None
    assert dto.service == Service.VK
    assert dto.service_id == "222_111"
    assert dto.title == "Song"
    assert dto.artists == ("Artist",)
    assert dto.duration_ms == 180_000
    assert dto.is_playable is True
    assert dto.direct_audio_url is None  # без with_url ссылку не отдаём
    assert dto.external_url == "https://vk.com/audio222_111"


def test_to_track_with_url():
    dto = _to_track(make_song(), with_url=True)
    assert dto.direct_audio_url == "https://cdn.test/a.mp3"


def test_to_track_without_url_is_not_playable():
    dto = _to_track(make_song(url=""), with_url=True)
    assert dto.is_playable is False
    assert dto.direct_audio_url is None


def test_to_track_invalid_returns_none():
    assert _to_track(None) is None
    assert _to_track(make_song(title="  ")) is None
    assert _to_track(make_song(track_id=0)) is None
    assert _to_track(make_song(owner_id=0)) is None


def test_to_track_no_artist_and_duration():
    dto = _to_track(make_song(artist=None, duration=None))
    assert dto.artists == ()
    assert dto.duration_ms is None


def test_to_playlist():
    dto = _to_playlist(make_playlist())
    assert dto.service_id == "1_2"
    assert dto.title == "My PL"
    assert dto.tracks_count == 1
    assert dto.artwork_url == "https://cdn.test/p.jpg"
    assert dto.external_url == "https://vk.com/music/playlist/1_2"


def test_to_playlist_with_access_key():
    dto = _to_playlist(make_playlist(access_key="abc"))
    assert dto.service_id == "1_2_abc"


def test_to_playlist_invalid_returns_none():
    assert _to_playlist(None) is None
    assert _to_playlist(make_playlist(title="")) is None
    assert _to_playlist(make_playlist(playlist_id=None)) is None


# ---------- конструктор и учётные данные ----------

def test_init_requires_token_and_user_agent():
    with pytest.raises(AdapterError) as exc:
        VkMusicAdapter("", "ua")
    assert exc.value.kind == ErrorKind.AUTH_FAILED
    with pytest.raises(AdapterError):
        VkMusicAdapter("token", "")


def test_init_validate_token_rejected(vk):
    vk.is_token_valid.return_value = False
    with pytest.raises(AdapterError) as exc:
        VkMusicAdapter("token", "ua", validate_token=True, min_interval=0)
    assert exc.value.kind == ErrorKind.AUTH_FAILED


def test_create_from_credentials_without_token_is_none():
    assert VkMusicAdapter.create_from_credentials(token=None) is None


def test_create_from_credentials_uses_user_agent_from_extra_data():
    with patch("services.music.vk.VkService") as service_cls:
        result = VkMusicAdapter.create_from_credentials(
            token="tok", extra_data=json.dumps({"user_agent": "UA"})
        )
    assert isinstance(result, VkMusicAdapter)
    service_cls.assert_called_once_with("UA", "tok")


def test_create_from_credentials_default_user_agent():
    with patch("services.music.vk.VkService") as service_cls:
        result = VkMusicAdapter.create_from_credentials(token="tok", extra_data="not json")
    assert isinstance(result, VkMusicAdapter)
    service_cls.assert_called_once_with(settings.VK_DEFAULT_USER_AGENT, "tok")


# ---------- поиск ----------

def test_search_tracks(adapter, vk):
    vk.search_songs_by_text.return_value = [make_song(), make_song(track_id=112)]
    result = adapter.search("query", limit=5)
    assert [t.service_id for t in result.tracks] == ["222_111", "222_112"]
    vk.search_songs_by_text.assert_called_once_with("query", count=5)


def test_search_respects_limit(adapter, vk):
    vk.search_songs_by_text.return_value = [make_song(track_id=i) for i in range(1, 6)]
    assert len(adapter.search("q", limit=2).tracks) == 2


def test_search_empty_query_makes_no_requests(adapter, vk):
    result = adapter.search("   ")
    assert result.tracks == ()
    vk.search_songs_by_text.assert_not_called()


def test_search_playlists(adapter, vk):
    vk.search_playlists_by_text.return_value = [make_playlist()]
    result = adapter.search("q", types=frozenset({SearchType.PLAYLIST}))
    assert len(result.playlists) == 1
    vk.search_songs_by_text.assert_not_called()


def test_search_artists_not_supported(adapter, vk):
    result = adapter.search("q", types=frozenset({SearchType.ARTIST}))
    assert result.tracks == ()
    assert len(result.errors) == 1
    assert result.errors[0].kind == ErrorKind.NOT_SUPPORTED
    assert result.errors[0].service == Service.VK
    vk.search_songs_by_text.assert_not_called()


# ---------- получение объектов ----------

def test_get_track_returns_url(adapter, vk):
    vk.get_songs_by_id.return_value = [make_song()]
    dto = adapter.get_track("222_111")
    assert dto is not None
    assert dto.direct_audio_url == "https://cdn.test/a.mp3"
    vk.get_songs_by_id.assert_called_once_with(["222_111"])


def test_get_track_not_found(adapter, vk):
    vk.get_songs_by_id.return_value = []
    assert adapter.get_track("222_111") is None


def test_get_track_unavailable_returns_none(adapter, vk):
    vk.get_songs_by_id.side_effect = RequestException("down")
    assert adapter.get_track("222_111") is None


def test_get_track_invalid_id_raises(adapter):
    with pytest.raises(AdapterError) as exc:
        adapter.get_track("not-an-id")
    assert exc.value.kind == ErrorKind.UNKNOWN


def test_get_artist_not_supported(adapter):
    with pytest.raises(AdapterError) as exc:
        adapter.get_artist("1")
    assert exc.value.kind == ErrorKind.NOT_SUPPORTED


def test_get_playlist_invalid_id_raises(adapter):
    with pytest.raises(AdapterError):
        adapter.get_playlist("garbage")


def test_get_playlist_with_tracks(adapter, vk):
    vk.get_playlists_by_userid.return_value = [make_playlist(count=1)]
    vk.get_songs_by_playlist_id.return_value = [make_song()]
    dto = adapter.get_playlist("1_2")
    assert dto is not None
    assert dto.title == "My PL"
    assert [t.service_id for t in dto.tracks] == ["222_111"]


# ---------- личная библиотека ----------

def test_get_user_favorites(adapter, vk):
    vk.get_songs_by_userid.return_value = [make_song()]
    tracks = adapter.get_user_favorites(account_id="222")
    assert len(tracks) == 1
    assert tracks[0].direct_audio_url == "https://cdn.test/a.mp3"
    vk.get_songs_by_userid.assert_called_once_with(222, count=50)


def test_get_user_favorites_without_account_id(adapter, vk):
    assert adapter.get_user_favorites(account_id=None) == []
    assert adapter.get_user_favorites(account_id="abc") == []
    vk.get_songs_by_userid.assert_not_called()


def test_get_user_favorites_swallows_errors(adapter, vk):
    vk.get_songs_by_userid.side_effect = RuntimeError("boom")
    assert adapter.get_user_favorites(account_id="222") == []


def test_get_user_playlists(adapter, vk):
    vk.get_playlists_by_userid.return_value = [make_playlist()]
    result = adapter.get_user_playlists(account_id="222")
    assert len(result) == 1
    vk.get_playlists_by_userid.assert_called_once_with(222, count=50)
    assert adapter.get_user_playlists(account_id=None) == []


# ---------- лайки ----------

def test_set_track_like_add_and_delete(adapter):
    with patch("vkpymusic.vk_api.make_request") as make_request, \
            patch("vkpymusic.vk_api.VkApiRequestBuilder") as builder:
        assert adapter.set_track_like("222_111", True) is True
        assert builder.build_from_base_request.call_args.kwargs["url"] == "audio.add"
        assert adapter.set_track_like("222_111", False) is True
        assert builder.build_from_base_request.call_args.kwargs["url"] == "audio.delete"
        assert make_request.call_count == 2


def test_set_track_like_invalid_id(adapter):
    assert adapter.set_track_like("garbage", True) is False


def test_set_track_like_failure_returns_false(adapter):
    with patch("vkpymusic.vk_api.make_request", side_effect=RuntimeError("x")):
        assert adapter.set_track_like("222_111", True) is False


# ---------- скачивание ----------

def test_save_mp3_downloads_and_caches(adapter, vk, tmp_path):
    vk.get_songs_by_id.return_value = [make_song()]
    response = SimpleNamespace(status_code=200, content=b"audio-bytes")
    with patch("services.music.vk.curl_requests.get", return_value=response) as get:
        path = adapter.save_mp3("222_111", tmp_path)
        again = adapter.save_mp3("222_111", tmp_path)
    assert path == tmp_path / "222_111.mp3"
    assert path.read_bytes() == b"audio-bytes"
    assert again == path
    assert get.call_count == 1  # второй раз берётся из кэша


def test_save_mp3_http_error(adapter, vk, tmp_path):
    vk.get_songs_by_id.return_value = [make_song()]
    response = SimpleNamespace(status_code=403, content=b"")
    with patch("services.music.vk.curl_requests.get", return_value=response):
        with pytest.raises(AdapterError) as exc:
            adapter.save_mp3("222_111", tmp_path)
    assert exc.value.kind == ErrorKind.UNAVAILABLE
    assert not (tmp_path / "222_111.mp3").exists()


def test_save_mp3_no_url(adapter, vk, tmp_path):
    vk.get_songs_by_id.return_value = [make_song(url="")]
    with pytest.raises(AdapterError) as exc:
        adapter.save_mp3("222_111", tmp_path)
    assert exc.value.kind == ErrorKind.UNAVAILABLE


def test_save_mp3_track_not_found(adapter, vk, tmp_path):
    vk.get_songs_by_id.return_value = []
    assert adapter.save_mp3("222_111", tmp_path) is None