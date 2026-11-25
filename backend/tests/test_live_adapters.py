"""Живые проверки адаптеров: реальная сеть и реальные токены.

По умолчанию всё пропускается. Запуск:
    RUN_LIVE_TESTS=1 pytest tests/test_live_adapters.py -v        (Linux/macOS)
    $env:RUN_LIVE_TESTS="1"; pytest tests/test_live_adapters.py -v  (PowerShell)

Токены (все необязательны, тесты без своего токена пропускаются):
    YANDEX_MUSIC_TOKEN   читается через app.config (.env подхватывается)
    VK_TOKEN             токен VK Музыки
    VK_USER_AGENT        user agent, под которым выдан токен (по умолчанию из настроек)
    VK_ACCOUNT_ID        числовой id вашего VK, для избранного и плейлистов
    YTMUSIC_AUTH_FILE    путь к JSON с авторизацией ytmusicapi (headers или oauth)

Тесты только читают данные: лайки, удаление и прочие изменения аккаунта не вызываются.
"""
import os
from pathlib import Path

import httpx
import pytest

from app.config import settings
from services.music.base import AdapterError
from services.music.dto import ErrorKind, SearchType
from services.music.vk import VkMusicAdapter
from services.music.yandex import YandexMusicAdapter
from services.music.youtube_music import YouTubeMusicAdapter

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        os.getenv("RUN_LIVE_TESTS") != "1",
        reason="живые тесты выключены: задайте RUN_LIVE_TESTS=1",
    ),
]

BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def assert_url_streams(url: str) -> None:
    """Ссылка реально отдаёт аудио: запрашиваем первый килобайт."""
    with httpx.stream(
        "GET", url,
        headers={"User-Agent": BROWSER_UA, "Range": "bytes=0-1023"},
        follow_redirects=True, timeout=30,
    ) as resp:
        assert resp.status_code in (200, 206), f"HTTP {resp.status_code}"
        assert next(resp.iter_bytes(), b""), "пустой ответ"


# ====================== Яндекс Музыка ======================

YANDEX_TOKEN = settings.YANDEX_MUSIC_TOKEN
needs_yandex = pytest.mark.skipif(not YANDEX_TOKEN, reason="нужен YANDEX_MUSIC_TOKEN")


@pytest.fixture(scope="module")
def yandex():
    return YandexMusicAdapter(token=YANDEX_TOKEN)


def test_yandex_search(yandex):
    result = yandex.search("Queen", limit=5)
    assert result.tracks
    assert all(t.title and t.service_id for t in result.tracks)


def test_yandex_search_other_types(yandex):
    result = yandex.search("Queen", types=frozenset({SearchType.ARTIST}), limit=3)
    assert result.artists


@needs_yandex
def test_yandex_track_has_working_audio_url(yandex):
    track = next(t for t in yandex.search("Queen", limit=10).tracks if t.is_playable)
    full = yandex.get_track(track.service_id)
    assert full is not None
    assert full.direct_audio_url and full.direct_audio_url.startswith("http")
    assert_url_streams(full.direct_audio_url)


@needs_yandex
def test_yandex_library(yandex):
    assert isinstance(yandex.get_user_playlists(limit=5), list)
    assert isinstance(yandex.get_user_favorites(limit=5), list)


def test_yandex_invalid_token_is_rejected():
    with pytest.raises(AdapterError) as exc:
        YandexMusicAdapter(token="definitely-not-a-valid-token")
    assert exc.value.kind == ErrorKind.AUTH_FAILED


# ====================== VK Музыка ======================

VK_TOKEN = settings.VK_TOKEN
VK_USER_AGENT = settings.VK_USER_AGENT or settings.VK_DEFAULT_USER_AGENT
VK_ACCOUNT_ID = settings.VK_ACCOUNT_ID
needs_vk = pytest.mark.skipif(not VK_TOKEN, reason="нужен VK_TOKEN")


@pytest.fixture(scope="module")
def vk():
    return VkMusicAdapter(VK_TOKEN, VK_USER_AGENT, validate_token=True)


@needs_vk
def test_vk_search(vk):
    result = vk.search("Queen", limit=5)
    assert result.tracks
    assert all("_" in t.service_id for t in result.tracks)


@needs_vk
def test_vk_track_has_working_audio_url(vk):
    track = next(t for t in vk.search("Queen", limit=10).tracks if t.is_playable)
    full = vk.get_track(track.service_id)
    assert full is not None
    assert full.direct_audio_url and full.direct_audio_url.startswith("http")
    assert_url_streams(full.direct_audio_url)


@needs_vk
@pytest.mark.skipif(not VK_ACCOUNT_ID, reason="нужен VK_ACCOUNT_ID")
def test_vk_library(vk):
    assert isinstance(vk.get_user_playlists(account_id=VK_ACCOUNT_ID, limit=5), list)
    assert isinstance(vk.get_user_favorites(account_id=VK_ACCOUNT_ID, limit=5), list)


def test_vk_invalid_token_is_rejected():
    with pytest.raises(AdapterError) as exc:
        VkMusicAdapter("invalid-token", VK_USER_AGENT, validate_token=True)
    assert exc.value.kind in (ErrorKind.AUTH_FAILED, ErrorKind.UNKNOWN)


# ====================== YouTube Music ======================

YT_AUTH_FILE = settings.YTMUSIC_AUTH_FILE
needs_yt_auth = pytest.mark.skipif(
    not (YT_AUTH_FILE and Path(YT_AUTH_FILE).is_file()),
    reason="нужен YTMUSIC_AUTH_FILE",
)


@pytest.fixture(scope="module")
def youtube():
    return YouTubeMusicAdapter(resolve_audio_url=False)


def test_youtube_search_without_auth(youtube):
    result = youtube.search("Daft Punk", limit=5)
    assert result.tracks
    assert all(len(t.service_id) == 11 for t in result.tracks)


def test_youtube_search_artists(youtube):
    result = youtube.search("Daft Punk", types=frozenset({SearchType.ARTIST}), limit=3)
    assert result.artists
    artist = youtube.get_artist(result.artists[0].service_id)
    assert artist is not None and artist.name


def test_youtube_get_track(youtube):
    first = youtube.search("Daft Punk Get Lucky", limit=3).tracks[0]
    track = youtube.get_track(first.service_id)
    assert track is not None
    assert track.title


def test_youtube_audio_url_via_ytdlp():
    adapter = YouTubeMusicAdapter(resolve_audio_url=True)
    first = adapter.search("Daft Punk Get Lucky", limit=3).tracks[0]
    track = adapter.get_track(first.service_id)
    if track is None or not track.direct_audio_url:
        pytest.skip("yt-dlp не вернул ссылку (не установлен или YouTube блокирует запрос)")
    assert_url_streams(track.direct_audio_url)


@needs_yt_auth
def test_youtube_library_with_auth():
    adapter = YouTubeMusicAdapter.create_from_credentials(
        token=Path(YT_AUTH_FILE).read_text(encoding="utf-8")
    )
    assert adapter is not None
    assert isinstance(adapter.get_user_playlists(limit=5), list)
    assert isinstance(adapter.get_user_favorites(limit=5), list)