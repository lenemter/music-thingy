"""Неофициальный адаптер VK Музыки на базе библиотеки vkpymusic.

Форматы service_id:
    трек      "{owner_id}_{audio_id}"                (допускается суффикс "_{access_key}")
    плейлист  "{owner_id}_{playlist_id}"             (допускается суффикс "_{access_key}")
    артист    не поддерживается

Токен и user agent: vkpymusic.TokenReceiver (логин/пароль, SMS, captcha).
"""
import logging
import re
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, ClassVar

from curl_cffi import requests as curl_requests
from curl_cffi.requests.exceptions import RequestException, Timeout
from vkpymusic import Service as VkService
from vkpymusic.utils import download_m3u8_as_mp3_pyav
from vkpymusic.vk_api import VkApiException

from .base import AdapterError, BaseMusicAdapter
from .dto import (ArtistDTO, ErrorKind, PlaylistDTO, SearchResultDTO,
                  SearchType, Service, ServiceErrorDTO, TrackDTO)

log = logging.getLogger(__name__)

_WEB_URL = "https://vk.com"

_PAGE_SIZE = 100
_MAX_PLAYLIST_SCAN_PAGES = 10

_TRACK_ID_RE = re.compile(r"^(-?\d+)_(\d+)(?:_(\w+))?$")
_PLAYLIST_ID_RE = _TRACK_ID_RE

# https://dev.vk.com/ru/reference/errors
_ERROR_KINDS: dict[int, ErrorKind] = {
    5: ErrorKind.AUTH_FAILED,       # user authorization failed
    17: ErrorKind.AUTH_FAILED,      # validation required
    6: ErrorKind.RATE_LIMIT,        # too many requests per second
    9: ErrorKind.RATE_LIMIT,        # flood control
    14: ErrorKind.RATE_LIMIT,       # captcha needed
    29: ErrorKind.QUOTA_EXCEEDED,   # rate limit reached
    10: ErrorKind.UNAVAILABLE,      # internal server error
    15: ErrorKind.UNAVAILABLE,      # access denied
    18: ErrorKind.UNAVAILABLE,      # user deleted or banned
    113: ErrorKind.UNAVAILABLE,     # invalid user id
    201: ErrorKind.UNAVAILABLE,     # audio access denied
    203: ErrorKind.UNAVAILABLE,     # access to group denied
}


@contextmanager
def _translate_errors() -> Iterator[None]:
    try:
        yield
    except AdapterError:
        raise
    except VkApiException as e:
        kind = _ERROR_KINDS.get(e.error_code, ErrorKind.UNKNOWN)
        raise AdapterError(kind, str(e), e.error_code or None) from e
    except Timeout as e:
        raise AdapterError(ErrorKind.TIMEOUT, str(e)) from e
    except (RequestException, OSError) as e:
        raise AdapterError(ErrorKind.UNAVAILABLE, str(e)) from e
    except (KeyError, ValueError, TypeError) as e:
        raise AdapterError(ErrorKind.UNKNOWN, f"Неожиданный ответ VK: {type(e).__name__}: {e}") from e


def _none_if_empty(value: Any) -> str | None:
    text = str(value).strip() if value is not None else ""
    return text or None


def _audio_ref(owner_id: Any, item_id: Any, access_key: str | None = None) -> str:
    ref = f"{owner_id}_{item_id}"
    return f"{ref}_{access_key}" if access_key else ref


def _to_track(s: Any, *, with_url: bool = False) -> TrackDTO | None:
    if s is None or not s.track_id or not s.owner_id or not _none_if_empty(s.title):
        return None

    artist = _none_if_empty(s.artist)
    url = _none_if_empty(s.url)
    is_playable = bool(url)
    ref = _audio_ref(s.owner_id, s.track_id)

    return TrackDTO(
        service=Service.VK,
        service_id=ref,
        title=str(s.title).strip(),
        artists=(artist,) if artist else (),
        is_playable=is_playable,
        duration_ms=int(s.duration) * 1000 if s.duration is not None and int(s.duration) >= 0 else None,
        direct_audio_url=url if (with_url and url and url.startswith("http")) else None,
        external_url=f"{_WEB_URL}/audio{ref}",
        artwork_url=None,
    )


def _to_playlist(p: Any, tracks: tuple[TrackDTO, ...] | None = None) -> PlaylistDTO | None:
    if p is None or p.owner_id is None or p.playlist_id is None or not _none_if_empty(p.title):
        return None
    access_key = _none_if_empty(p.access_key)
    ref = _audio_ref(p.owner_id, p.playlist_id, access_key)
    return PlaylistDTO(
        service=Service.VK,
        service_id=ref,
        title=str(p.title).strip(),
        description=_none_if_empty(p.description),
        owner_name=None,
        tracks_count=p.count,
        artwork_url=_none_if_empty(p.photo),
        external_url=f"{_WEB_URL}/music/playlist/{ref}",
        tracks=tracks,
    )


class VkMusicAdapter(BaseMusicAdapter):
    service: ClassVar[Service] = Service.VK
    official: ClassVar[bool] = False

    def __init__(
        self,
        token: str,
        user_agent: str,
        *,
        validate_token: bool = False,
        min_interval: float = 0.35,
        playlist_limit: int | None = 200,
    ) -> None:
        """
        token / user_agent  -- из vkpymusic.TokenReceiver.
        validate_token      -- сразу проверить токен запросом к VK.
        min_interval        -- минимальная пауза между запросами к VK в секундах.
        playlist_limit      -- максимум треков, загружаемых в get_playlist.
        """
        if not token or not user_agent:
            raise AdapterError(ErrorKind.AUTH_FAILED, "Для VK нужны и token, и user_agent")
        self._setup(VkService(user_agent, token), validate_token=validate_token,
                    min_interval=min_interval, playlist_limit=playlist_limit)

    @classmethod
    def from_config(cls, filename: str = "config_vk.ini", *, validate_token: bool = False,
                    min_interval: float = 0.35, playlist_limit: int | None = 200) -> "VkMusicAdapter":
        """Создаёт адаптер из конфига, сохранённого TokenReceiver.save_to_config()."""
        vk = VkService.parse_config(filename)
        if vk is None:
            raise AdapterError(ErrorKind.AUTH_FAILED, f"Конфиг VK {filename!r} не найден или повреждён")
        self = cls.__new__(cls)
        self._setup(vk, validate_token=validate_token, min_interval=min_interval,
                    playlist_limit=playlist_limit)
        return self

    def _setup(self, vk: VkService, *, validate_token: bool, min_interval: float,
               playlist_limit: int | None) -> None:
        self._vk = vk
        self._min_interval = max(0.0, min_interval)
        self._playlist_limit = playlist_limit
        self._lock = threading.Lock()
        self._last_call = 0.0
        if validate_token:
            with self._throttled(), _translate_errors():
                valid = vk.is_token_valid()
            if not valid:
                raise AdapterError(ErrorKind.AUTH_FAILED, "VK отклонил токен", 401)

    @contextmanager
    def _throttled(self) -> Iterator[None]:
        with self._lock:
            wait = self._last_call + self._min_interval - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            try:
                yield
            finally:
                self._last_call = time.monotonic()

    def search(self, query: str, types: frozenset[SearchType] = frozenset({SearchType.TRACK}),
               limit: int = 10) -> SearchResultDTO:
        query = query.strip()
        if not query or limit <= 0:
            return SearchResultDTO(query=query)

        count = min(limit, _PAGE_SIZE)
        tracks: tuple[TrackDTO, ...] = ()
        playlists: tuple[PlaylistDTO, ...] = ()
        errors: tuple[ServiceErrorDTO, ...] = ()

        if SearchType.TRACK in types:
            with self._throttled(), _translate_errors():
                songs = self._vk.search_songs_by_text(query, count=count)
            tracks = tuple(d for s in songs or [] if (d := _to_track(s)))[:limit]

        if SearchType.PLAYLIST in types:
            with self._throttled(), _translate_errors():
                found = self._vk.search_playlists_by_text(query, count=count)
            playlists = tuple(d for p in found or [] if (d := _to_playlist(p)))[:limit]

        if SearchType.ARTIST in types:
            errors += (ServiceErrorDTO(service=Service.VK, kind=ErrorKind.NOT_SUPPORTED,
                                       message="Поиск артистов в VK не поддерживается"),)

        return SearchResultDTO(query=query, tracks=tracks, playlists=playlists, errors=errors)

    def _fetch_song(self, service_id: str) -> Any | None:
        sid = service_id.strip()
        if not _TRACK_ID_RE.match(sid):
            raise AdapterError(ErrorKind.UNKNOWN,
                               f"Некорректный id трека {service_id!r}, ожидается 'owner_id_audio_id'")
        try:
            with self._throttled(), _translate_errors():
                found = self._vk.get_songs_by_id([sid])
        except AdapterError as e:
            if e.kind is ErrorKind.UNAVAILABLE or e.status_code == 100:
                return None
            raise
        return found[0] if found else None

    def get_track(self, service_id: str) -> TrackDTO | None:
        song = self._fetch_song(service_id)
        return _to_track(song, with_url=True) if song is not None else None

    def save_mp3(self, service_id: str, directory: str | Path = "music_cache", *,
                 overwrite: bool = False) -> Path | None:
        song = self._fetch_song(service_id)
        if song is None:
            return None
        url = _none_if_empty(song.url)
        if not url:
            raise AdapterError(ErrorKind.UNAVAILABLE, f"У трека {service_id} нет ссылки на аудио")

        path = Path(directory) / f"{service_id.strip()}.mp3"
        if path.exists() and not overwrite:
            return path
        path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with _translate_errors():
                if ".m3u8" in url:
                    download_m3u8_as_mp3_pyav(url, str(path))
                else:
                    resp = curl_requests.get(url, timeout=60)
                    if resp.status_code != 200:
                        raise AdapterError(ErrorKind.UNAVAILABLE,
                                           f"Скачивание {service_id}: HTTP {resp.status_code}", resp.status_code)
                    path.write_bytes(resp.content)
        except RuntimeError as e:  # так vkpymusic сообщает о сбое сборки или конвертации HLS
            path.unlink(missing_ok=True)
            raise AdapterError(ErrorKind.UNKNOWN, f"Не удалось скачать {service_id}: {e}") from e
        except BaseException:
            path.unlink(missing_ok=True)
            raise
        return path

    def get_artist(self, service_id: str) -> ArtistDTO | None:
        raise AdapterError(ErrorKind.NOT_SUPPORTED, "VK не предоставляет данных об артистах")

    def _find_user_playlist(self, owner_id: int, playlist_id: int) -> Any | None:
        for page in range(_MAX_PLAYLIST_SCAN_PAGES):
            with self._throttled(), _translate_errors():
                batch = self._vk.get_playlists_by_userid(owner_id, count=_PAGE_SIZE, offset=page * _PAGE_SIZE)
            for p in batch or []:
                if p.playlist_id == playlist_id:
                    return p
            if len(batch or []) < _PAGE_SIZE:
                break
        return None

    def get_playlist(self, service_id: str) -> PlaylistDTO | None:
        m = _PLAYLIST_ID_RE.match(service_id.strip())
        if not m:
            raise AdapterError(ErrorKind.UNKNOWN,
                               f"Некорректный id плейлиста {service_id!r}, ожидается 'owner_id_playlist_id[_access_key]'")
        owner_id, playlist_id, access_key = int(m.group(1)), int(m.group(2)), m.group(3)

        try:
            meta = self._find_user_playlist(owner_id, playlist_id)
        except AdapterError as e:
            if e.kind is not ErrorKind.UNAVAILABLE:
                raise
            if not access_key:
                return None
            meta = None

        key = _none_if_empty(getattr(meta, "access_key", None)) or access_key
        if meta is None and not key:
            return None

        limit = self._playlist_limit
        if meta is not None and meta.count is not None:
            limit = meta.count if limit is None else min(limit, meta.count)

        songs: list[Any] = []
        try:
            while limit is None or len(songs) < limit:
                page_size = _PAGE_SIZE if limit is None else min(_PAGE_SIZE, limit - len(songs))
                with self._throttled(), _translate_errors():
                    batch = self._vk.get_songs_by_playlist_id(
                        owner_id, playlist_id, key or "", count=page_size, offset=len(songs))
                songs.extend(batch or [])
                if len(batch or []) < page_size:
                    break
        except AdapterError as e:
            if e.kind is ErrorKind.UNAVAILABLE:
                return None
            raise

        tracks = tuple(d for s in songs if (d := _to_track(s)))
        if meta is not None:
            return _to_playlist(meta, tracks=tracks)
        ref = _audio_ref(owner_id, playlist_id, key)
        return PlaylistDTO(
            service=Service.VK,
            service_id=ref,
            title=f"Плейлист VK {owner_id}_{playlist_id}",
            tracks_count=len(tracks),
            external_url=f"{_WEB_URL}/music/playlist/{ref}",
            tracks=tracks,
        )
