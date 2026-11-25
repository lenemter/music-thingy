from unittest.mock import MagicMock, patch

import pytest
from ytmusicapi import LikeStatus
from ytmusicapi.exceptions import YTMusicError

from services.music.base import AdapterError
from services.music.dto import ErrorKind, PlaybackKind, SearchType, Service
from services.music.youtube_music import (
    YouTubeMusicAdapter,
    _artist_refs,
    _best_thumbnail,
    _kind_from_message,
    _parse_duration_ms,
    _resolve_audio_url,
    _to_artist,
    _to_playlist,
    _to_track,
    _translate_errors,
)

VIDEO_ID = "dQw4w9WgXcQ"
CHANNEL_ID = "UC" + "a" * 22


def make_item(**kw):
    data = {
        "videoId": VIDEO_ID,
        "title": "Song",
        "artists": [{"name": "Artist", "id": CHANNEL_ID}],
        "album": {"name": "Album"},
        "duration_seconds": 212,
        "thumbnails": [
            {"url": "https://img/small", "width": 10, "height": 10},
            {"url": "https://img/big", "width": 100, "height": 100},
        ],
        "isAvailable": True,
    }
    data.update(kw)
    return data


@pytest.fixture
def yt():
    with patch("services.music.youtube_music.YTMusic") as ytmusic_cls:
        yield ytmusic_cls.return_value


@pytest.fixture
def adapter(yt):
    return YouTubeMusicAdapter(resolve_audio_url=False)


# ---------- вспомогательные функции ----------

def test_best_thumbnail_picks_largest():
    assert _best_thumbnail(make_item()["thumbnails"]) == "https://img/big"
    assert _best_thumbnail([]) is None
    assert _best_thumbnail(None) is None
    assert _best_thumbnail([{"url": "not-http", "width": 1, "height": 1}]) is None


def test_parse_duration_ms():
    assert _parse_duration_ms({"duration_seconds": 212}) == 212_000
    assert _parse_duration_ms({"duration": "3:32"}) == 212_000
    assert _parse_duration_ms({"duration": "1:02:03"}) == 3_723_000
    assert _parse_duration_ms({"duration": "abc"}) is None
    assert _parse_duration_ms({}) is None


def test_artist_refs_ids_only_if_all_present():
    names, ids = _artist_refs({"artists": [{"name": "A", "id": "1"}, {"name": "B", "id": "2"}]})
    assert names == ("A", "B")
    assert ids == ("1", "2")

    names, ids = _artist_refs({"artists": [{"name": "A", "id": "1"}, {"name": "B"}]})
    assert names == ("A", "B")
    assert ids == ()


def test_artist_refs_falls_back_to_artist_field():
    names, ids = _artist_refs({"artist": " Solo "})
    assert names == ("Solo",)
    assert ids == ()


def test_kind_from_message():
    assert _kind_from_message("HTTP 429 Too Many Requests") == (ErrorKind.RATE_LIMIT, 429)
    assert _kind_from_message("Please sign in")[0] == ErrorKind.AUTH_FAILED
    assert _kind_from_message("HTTP 404") == (ErrorKind.UNAVAILABLE, 404)
    assert _kind_from_message("HTTP 503") == (ErrorKind.UNAVAILABLE, 503)
    assert _kind_from_message("request timed out")[0] == ErrorKind.TIMEOUT
    assert _kind_from_message("something weird") == (ErrorKind.UNKNOWN, None)


def test_translate_errors():
    with pytest.raises(AdapterError) as exc, _translate_errors():
        raise YTMusicError("HTTP 429")
    assert exc.value.kind == ErrorKind.RATE_LIMIT
    assert exc.value.status_code == 429

    with pytest.raises(AdapterError) as exc, _translate_errors():
        raise TimeoutError("slow")
    assert exc.value.kind == ErrorKind.TIMEOUT

    with pytest.raises(AdapterError) as exc, _translate_errors():
        raise OSError("boom")
    assert exc.value.kind == ErrorKind.UNAVAILABLE


# ---------- конвертеры ----------

def test_to_track():
    dto = _to_track(make_item())
    assert dto is not None
    assert dto.service == Service.YOUTUBE
    assert dto.service_id == VIDEO_ID
    assert dto.title == "Song"
    assert dto.artists == ("Artist",)
    assert dto.artist_ids == (CHANNEL_ID,)
    assert dto.album == "Album"
    assert dto.duration_ms == 212_000
    assert dto.artwork_url == "https://img/big"
    assert dto.playback.kind == PlaybackKind.YOUTUBE_IFRAME
    assert dto.playback.ref == VIDEO_ID
    assert dto.external_url == f"https://music.youtube.com/watch?v={VIDEO_ID}"


def test_to_track_album_as_string():
    assert _to_track(make_item(album="Plain")).album == "Plain"


def test_to_track_unavailable_has_no_playback():
    dto = _to_track(make_item(isAvailable=False))
    assert dto.is_playable is False
    assert dto.playback is None


def test_to_track_invalid_returns_none():
    assert _to_track(None) is None
    assert _to_track(make_item(videoId="short")) is None
    assert _to_track(make_item(videoId=None)) is None
    assert _to_track(make_item(title="")) is None


def test_to_track_keeps_direct_audio_url():
    assert _to_track(make_item(), direct_audio_url="https://a").direct_audio_url == "https://a"


def test_to_artist():
    dto = _to_artist({"name": "Queen", "browseId": CHANNEL_ID, "thumbnails": make_item()["thumbnails"]})
    assert dto.service_id == CHANNEL_ID
    assert dto.name == "Queen"
    assert dto.artwork_url == "https://img/big"
    assert dto.external_url == f"https://music.youtube.com/channel/{CHANNEL_ID}"


def test_to_artist_explicit_channel_id_and_invalid():
    assert _to_artist({"name": "Q"}, channel_id=CHANNEL_ID).service_id == CHANNEL_ID
    assert _to_artist({"name": "Q"}) is None
    assert _to_artist({"browseId": CHANNEL_ID}) is None
    assert _to_artist(None) is None


def test_to_playlist():
    dto = _to_playlist({
        "id": "VLPL123", "title": "Mix", "author": {"name": "Me"},
        "trackCount": 5, "thumbnails": make_item()["thumbnails"],
    })
    assert dto.service_id == "PL123"  # префикс VL отбрасывается
    assert dto.title == "Mix"
    assert dto.owner_name == "Me"
    assert dto.tracks_count == 5
    assert dto.external_url == "https://music.youtube.com/playlist?list=PL123"


def test_to_playlist_item_count_string_and_invalid():
    assert _to_playlist({"playlistId": "PL1", "title": "T", "itemCount": "12 songs"}).tracks_count == 12
    assert _to_playlist({"playlistId": "PL1", "title": "T", "itemCount": "1,234 songs"}).tracks_count == 1234
    assert _to_playlist({"playlistId": "PL1", "title": ""}) is None
    assert _to_playlist({"title": "T"}) is None
    assert _to_playlist(None) is None


def test_to_playlist_count_from_tracks():
    track = _to_track(make_item())
    dto = _to_playlist({"id": "PL1", "title": "T"}, tracks=(track,))
    assert dto.tracks_count == 1


# ---------- поиск ----------

def test_search_tracks(adapter, yt):
    yt.search.return_value = [make_item()]
    result = adapter.search("query", limit=3)
    assert len(result.tracks) == 1
    yt.search.assert_called_once_with("query", filter="songs", limit=3, ignore_spelling=True)


def test_search_artists_and_playlists(adapter, yt):
    yt.search.side_effect = [
        [{"name": "Queen", "browseId": CHANNEL_ID}],
        [{"browseId": "VLPL1", "title": "Mix"}],
    ]
    result = adapter.search("q", types=frozenset({SearchType.ARTIST, SearchType.PLAYLIST}))
    assert [a.name for a in result.artists] == ["Queen"]
    assert [p.service_id for p in result.playlists] == ["PL1"]


def test_search_empty_query(adapter, yt):
    assert adapter.search("  ").tracks == ()
    yt.search.assert_not_called()


# ---------- получение объектов ----------

def test_get_track(adapter, yt):
    yt.get_watch_playlist.return_value = {"tracks": [make_item()]}
    dto = adapter.get_track(VIDEO_ID)
    assert dto.service_id == VIDEO_ID
    assert dto.direct_audio_url is None  # resolve_audio_url=False


def test_get_track_ignores_id_suffix(adapter, yt):
    yt.get_watch_playlist.return_value = {"tracks": [make_item()]}
    assert adapter.get_track(f"{VIDEO_ID}:whatever") is not None
    assert yt.get_watch_playlist.call_args.kwargs["videoId"] == VIDEO_ID


def test_get_track_resolves_audio_url(yt):
    yt.get_watch_playlist.return_value = {"tracks": [make_item()]}
    with patch("services.music.youtube_music._resolve_audio_url", return_value="https://audio"):
        dto = YouTubeMusicAdapter().get_track(VIDEO_ID)
    assert dto.direct_audio_url == "https://audio"


def test_get_track_not_found(adapter, yt):
    yt.get_watch_playlist.return_value = {"tracks": []}
    assert adapter.get_track(VIDEO_ID) is None
    yt.get_watch_playlist.return_value = {"tracks": [make_item(videoId="otherVideo1")]}
    assert adapter.get_track(VIDEO_ID) is None


def test_get_track_unavailable_returns_none(adapter, yt):
    yt.get_watch_playlist.side_effect = YTMusicError("HTTP 404")
    assert adapter.get_track(VIDEO_ID) is None


def test_get_track_other_error_raises(adapter, yt):
    yt.get_watch_playlist.side_effect = YTMusicError("HTTP 429")
    with pytest.raises(AdapterError) as exc:
        adapter.get_track(VIDEO_ID)
    assert exc.value.kind == ErrorKind.RATE_LIMIT


def test_get_track_invalid_id(adapter):
    with pytest.raises(AdapterError) as exc:
        adapter.get_track("bad")
    assert exc.value.kind == ErrorKind.UNKNOWN


def test_get_artist(adapter, yt):
    yt.get_artist.return_value = {"name": "Queen", "thumbnails": []}
    dto = adapter.get_artist(CHANNEL_ID)
    assert dto.name == "Queen"
    assert dto.service_id == CHANNEL_ID
    with pytest.raises(AdapterError):
        adapter.get_artist("not-a-channel")


def test_get_playlist(adapter, yt):
    yt.get_playlist.return_value = {"id": "PL1", "title": "Mix", "tracks": [make_item()]}
    dto = adapter.get_playlist("VLPL1")
    yt.get_playlist.assert_called_once_with("PL1", limit=200)
    assert dto.service_id == "PL1"
    assert len(dto.tracks) == 1


def test_get_playlist_unavailable_and_empty_id(adapter, yt):
    yt.get_playlist.side_effect = YTMusicError("HTTP 404")
    assert adapter.get_playlist("PL1") is None
    with pytest.raises(AdapterError):
        adapter.get_playlist("  ")


# ---------- учётные данные и библиотека ----------

def test_create_from_credentials_without_data_is_none():
    assert YouTubeMusicAdapter.create_from_credentials() is None


def test_create_from_credentials_parses_json_token():
    with patch("services.music.youtube_music.YTMusic") as ytmusic_cls:
        result = YouTubeMusicAdapter.create_from_credentials(token='{"a": 1}')
    assert isinstance(result, YouTubeMusicAdapter)
    assert ytmusic_cls.call_args.kwargs["auth"] == {"a": 1}


def test_create_from_credentials_uses_extra_data_when_no_token():
    with patch("services.music.youtube_music.YTMusic") as ytmusic_cls:
        YouTubeMusicAdapter.create_from_credentials(extra_data='{"b": 2}')
    assert ytmusic_cls.call_args.kwargs["auth"] == {"b": 2}


def test_get_user_playlists(adapter, yt):
    yt.get_library_playlists.return_value = [{"playlistId": "PL1", "title": "Mine"}]
    result = adapter.get_user_playlists(limit=10)
    assert [p.service_id for p in result] == ["PL1"]
    yt.get_library_playlists.assert_called_once_with(limit=10)


def test_get_user_playlists_swallows_errors(adapter, yt):
    yt.get_library_playlists.side_effect = RuntimeError("boom")
    assert adapter.get_user_playlists() == []


def test_get_user_favorites(adapter, yt):
    yt.get_liked_songs.return_value = {"tracks": [make_item()]}
    result = adapter.get_user_favorites(limit=5)
    assert [t.service_id for t in result] == [VIDEO_ID]
    yt.get_liked_songs.assert_called_once_with(limit=5)


def test_get_user_favorites_swallows_errors(adapter, yt):
    yt.get_liked_songs.side_effect = RuntimeError("boom")
    assert adapter.get_user_favorites() == []


def test_set_track_like(adapter, yt):
    assert adapter.set_track_like(VIDEO_ID, True) is True
    yt.rate_song.assert_called_with(VIDEO_ID, rating=LikeStatus.LIKE)
    assert adapter.set_track_like(VIDEO_ID, False) is True
    yt.rate_song.assert_called_with(VIDEO_ID, rating=LikeStatus.INDIFFERENT)


def test_set_track_like_failure(adapter, yt):
    yt.rate_song.side_effect = RuntimeError("boom")
    assert adapter.set_track_like(VIDEO_ID, True) is False


# ---------- выбор аудио-ссылки через yt-dlp ----------

def _mock_ydl(info):
    ydl_cls = MagicMock()
    ydl_cls.return_value.__enter__.return_value.extract_info.return_value = info
    return ydl_cls


def test_resolve_audio_url_picks_best_audio_only_format():
    info = {"formats": [
        {"url": "https://low", "acodec": "opus", "vcodec": "none", "protocol": "https", "abr": 50},
        {"url": "https://high", "acodec": "opus", "vcodec": "none", "protocol": "https", "abr": 130},
        {"url": "https://video", "acodec": "aac", "vcodec": "avc1", "protocol": "https", "abr": 999},
        {"url": "https://hls", "acodec": "aac", "vcodec": "none", "protocol": "m3u8_native", "abr": 500},
    ]}
    with patch("yt_dlp.YoutubeDL", _mock_ydl(info)):
        assert _resolve_audio_url(VIDEO_ID, None) == "https://high"


def test_resolve_audio_url_falls_back_to_info_url():
    with patch("yt_dlp.YoutubeDL", _mock_ydl({"formats": [], "url": "https://direct"})):
        assert _resolve_audio_url(VIDEO_ID, None) == "https://direct"


def test_resolve_audio_url_no_info():
    with patch("yt_dlp.YoutubeDL", _mock_ydl(None)):
        assert _resolve_audio_url(VIDEO_ID, None) is None
