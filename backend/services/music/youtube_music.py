from __future__ import annotations

"""Неофициальный адаптер YouTube Music: метаданные через ytmusicapi, аудио-ссылка через yt-dlp.

Форматы service_id:
    трек      "{video_id}"        (11 символов; допускается "{video_id}:что-угодно", хвост игнорируется)
    артист    "{channel_id}"      (UC...)
    плейлист  "{playlist_id}"     (PL..., OLAK5uy_... и т.п.; префикс "VL" отбрасывается)

Без авторизации работает поиск и публичные данные. Для приватных плейлистов и библиотеки нужен auth, он пробрасывается в конструктор.
"""
import json
import logging
import re
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any, ClassVar, Literal

from ytmusicapi import LikeStatus, YTMusic
from ytmusicapi.exceptions import YTMusicError

from .base import AdapterError, BaseMusicAdapter
from .dto import (ArtistDTO, ErrorKind, PlaybackDTO, PlaybackKind,
                  PlaylistDTO, SearchResultDTO, SearchType, Service, TrackDTO)

log = logging.getLogger(__name__)

_WEB_URL = "https://music.youtube.com"

_SEARCH_FILTERS: dict[SearchType, Any] = {
    SearchType.TRACK: "songs",
    SearchType.ARTIST: "artists",
    SearchType.PLAYLIST: "playlists",
}

_VIDEO_ID_RE = re.compile(r"^[\w-]{11}$")
_CHANNEL_ID_RE = re.compile(r"UC[\w-]{22}")
_HTTP_STATUS_RE = re.compile(r"\b(?:HTTP|status(?: code)?)\D{0,3}(\d{3})\b", re.IGNORECASE)
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def _kind_from_message(msg: str) -> tuple[ErrorKind, int | None]:
    low = msg.lower()
    m = _HTTP_STATUS_RE.search(msg)
    status = int(m.group(1)) if m else None
    if status == 429 or "too many requests" in low:
        return ErrorKind.RATE_LIMIT, 429
    if status in (401, 403) or "sign in" in low or "login" in low:
        return ErrorKind.AUTH_FAILED, status
    if (status in (400, 404) or "unavailable" in low or "not found" in low or "does not exist" in low
            or "no content returned" in low or "private playlist" in low):
        return ErrorKind.UNAVAILABLE, status
    if "timed out" in low or "timeout" in low:
        return ErrorKind.TIMEOUT, status
    if status is not None and status >= 500:
        return ErrorKind.UNAVAILABLE, status
    return ErrorKind.UNKNOWN, status


@contextmanager
def _translate_errors() -> Iterator[None]:
    try:
        yield
    except AdapterError:
        raise
    except TimeoutError as e:
        raise AdapterError(ErrorKind.TIMEOUT, str(e)) from e
    except YTMusicError as e:
        kind, status = _kind_from_message(str(e))
        raise AdapterError(kind, str(e), status) from e
    except OSError as e:
        msg = str(e)
        kind, status = _kind_from_message(msg)
        if kind is ErrorKind.UNKNOWN:
            kind = ErrorKind.UNAVAILABLE
        raise AdapterError(kind, msg, status) from e


def _best_thumbnail(thumbs: Any) -> str | None:
    if not isinstance(thumbs, list):
        return None
    ok = [t for t in thumbs if isinstance(t, dict) and str(t.get("url", "")).startswith("http")]
    best = max(ok, key=lambda t: (t.get("width") or 0) * (t.get("height") or 0), default=None)
    return best["url"] if best else None


def _parse_duration_ms(item: dict[str, Any]) -> int | None:
    secs = item.get("duration_seconds")
    if isinstance(secs, (int, float)) and secs >= 0:
        return int(secs * 1000)
    raw = item.get("duration") or item.get("length")
    if isinstance(raw, str) and re.fullmatch(r"\d+(:\d{1,2}){1,2}", raw):
        total = 0
        for part in raw.split(":"):
            total = total * 60 + int(part)
        return total * 1000
    return None


def _artist_refs(item: dict[str, Any]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """(имена, id). id возвращаются только если есть у всех исполнителей."""
    raw = [a for a in item.get("artists") or [] if isinstance(a, dict) and a.get("name")]
    names = tuple(str(a["name"]).strip() for a in raw)
    ids = tuple(str(a["id"]) for a in raw if a.get("id"))
    if not names and item.get("artist"):
        names = (str(item["artist"]).strip(),)
    return names, (ids if names and len(ids) == len(names) else ())


def _to_track(item: dict[str, Any] | None, *, direct_audio_url: str | None = None) -> TrackDTO | None:
    if not item:
        return None
    vid = item.get("videoId")
    title = item.get("title")
    if not isinstance(vid, str) or not _VIDEO_ID_RE.match(vid) or not title:
        return None

    names, ids = _artist_refs(item)
    album = item.get("album")
    album_name = album.get("name") if isinstance(album, dict) else (album if isinstance(album, str) else None)
    is_playable = item.get("isAvailable", True) is not False

    return TrackDTO(
        service=Service.YOUTUBE,
        service_id=vid,
        title=str(title),
        artists=names,
        is_playable=is_playable,
        artist_ids=ids,
        duration_ms=_parse_duration_ms(item),
        album=album_name or None,
        playback=PlaybackDTO(kind=PlaybackKind.YOUTUBE_IFRAME, ref=vid) if is_playable else None,
        direct_audio_url=direct_audio_url,
        external_url=f"{_WEB_URL}/watch?v={vid}",
        artwork_url=_best_thumbnail(item.get("thumbnails") or item.get("thumbnail")),
    )


def _to_artist(item: dict[str, Any] | None, *, channel_id: str | None = None) -> ArtistDTO | None:
    if not item:
        return None
    raw_id = channel_id or item.get("channelId") or item.get("browseId") or ""
    m = _CHANNEL_ID_RE.search(str(raw_id))
    name = item.get("name") or item.get("artist")
    if not m or not name:
        return None
    cid = m.group(0)
    return ArtistDTO(
        service=Service.YOUTUBE,
        service_id=cid,
        name=str(name),
        artwork_url=_best_thumbnail(item.get("thumbnails")),
        external_url=f"{_WEB_URL}/channel/{cid}",
    )


def _to_playlist(item: dict[str, Any] | None, *, tracks: tuple[TrackDTO, ...] | None = None,
                 playlist_id: str | None = None) -> PlaylistDTO | None:
    if not item:
        return None
    pid = str(playlist_id or item.get("id") or item.get("playlistId") or item.get("browseId") or "")
    pid = pid.removeprefix("VL")
    title = item.get("title")
    if not pid or not title:
        return None

    author = item.get("author")
    owner = author.get("name") if isinstance(author, dict) else (author if isinstance(author, str) else None)

    count = item.get("trackCount")
    if not isinstance(count, int):
        raw = str(item.get("itemCount") or "")
        digits = re.search(r"\d[\d,\s]*", raw)
        count = int(re.sub(r"\D", "", digits.group(0))) if digits else None
    if count is None and tracks is not None:
        count = len(tracks)

    return PlaylistDTO(
        service=Service.YOUTUBE,
        service_id=pid,
        title=str(title),
        description=item.get("description") or None,
        owner_name=owner or None,
        tracks_count=count,
        artwork_url=_best_thumbnail(item.get("thumbnails")),
        external_url=f"{_WEB_URL}/playlist?list={pid}",
        tracks=tracks,
    )


class _QuietLogger:

    def _log(self, msg: str) -> None:
        log.debug("yt-dlp: %s", _ANSI_RE.sub("", msg))

    debug = info = warning = error = _log

def _resolve_audio_url(video_id: str, ydl_opts: dict[str, Any] | None) -> str | None:
    try:
        from yt_dlp import YoutubeDL
        from yt_dlp.utils import YoutubeDLError
    except ImportError:
        log.info("yt-dlp не установлен: direct_audio_url не будет заполнен")
        return None
    opts: dict[str, Any] = {
        "quiet": True, "no_warnings": True, "no_color": True, "skip_download": True,
        "noplaylist": True, "format": "bestaudio/best", "socket_timeout": 15,
        "logger": _QuietLogger(),
        **(ydl_opts or {}),
    }
    try:
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(f"{_WEB_URL}/watch?v={video_id}", download=False)
    except YoutubeDLError as e:
        log.warning("Не удалось получить прямую ссылку для %s: %s", video_id, _ANSI_RE.sub("", str(e)))
        return None
    if not isinstance(info, dict):
        return None
    formats = [
        f for f in info.get("formats") or []
        if f.get("url") and f.get("acodec") not in (None, "none") and f.get("vcodec") in (None, "none")
        and str(f.get("protocol", "")).startswith("http") and "m3u8" not in str(f.get("protocol", ""))
    ]
    best = max(formats, key=lambda f: f.get("abr") or f.get("tbr") or 0, default=None)
    if best:
        return best["url"]
    url = info.get("url")
    return url if isinstance(url, str) and url.startswith("http") else None


class YouTubeMusicAdapter(BaseMusicAdapter):
    service: ClassVar[Service] = Service.YOUTUBE
    official: ClassVar[bool] = False

    def __init__(
        self,
        *,
        auth: Any = None,
        language: str = "en",
        location: str = "",
        proxies: dict[str, str] | None = None,
        resolve_audio_url: bool = True,
        playlist_limit: int | None = 200,
        ydl_opts: dict[str, Any] | None = None,
    ) -> None:
        kwargs: dict[str, Any] = {"language": language}
        if auth is not None:
            kwargs["auth"] = auth
        if location:
            kwargs["location"] = location
        if proxies:
            kwargs["proxies"] = proxies
        with _translate_errors():
            self._yt = YTMusic(**kwargs)
        self._resolve_audio_url = resolve_audio_url
        self._playlist_limit = playlist_limit
        self._ydl_opts = ydl_opts

    def search(self, query: str, types: frozenset[SearchType] = frozenset({SearchType.TRACK}),
               limit: int = 10) -> SearchResultDTO:
        query = query.strip()
        if not query or limit <= 0:
            return SearchResultDTO(query=query)

        tracks: tuple[TrackDTO, ...] = ()
        artists: tuple[ArtistDTO, ...] = ()
        playlists: tuple[PlaylistDTO, ...] = ()

        for search_type in SearchType:
            if search_type not in types:
                continue
            with _translate_errors():
                items = self._yt.search(query, filter=_SEARCH_FILTERS[search_type],
                                        limit=limit, ignore_spelling=True)
            items = [i for i in items or [] if isinstance(i, dict)]
            if search_type is SearchType.TRACK:
                tracks = tuple(dt for i in items if (dt := _to_track(i)))[:limit]
            elif search_type is SearchType.ARTIST:
                artists = tuple(da for i in items if (da := _to_artist(i)))[:limit]
            else:
                playlists = tuple(dp for i in items if (dp := _to_playlist(i)))[:limit]

        return SearchResultDTO(query=query, tracks=tracks, artists=artists, playlists=playlists)

    def get_track(self, service_id: str) -> TrackDTO | None:
        vid = service_id.partition(":")[0].strip()
        if not _VIDEO_ID_RE.match(vid):
            raise AdapterError(ErrorKind.UNKNOWN, f"Некорректный id трека {service_id!r}, ожидается 11-символьный videoId")
        try:
            with _translate_errors():
                data = self._yt.get_watch_playlist(videoId=vid, limit=1)
        except AdapterError as e:
            if e.kind is ErrorKind.UNAVAILABLE:
                return None
            raise
        items = [t for t in (data or {}).get("tracks") or [] if isinstance(t, dict)]
        item = next((t for t in items if t.get("videoId") == vid), None)
        if item is None:
            return None
        url = _resolve_audio_url(vid, self._ydl_opts) if self._resolve_audio_url else None
        return _to_track(item, direct_audio_url=url)

    def get_artist(self, service_id: str) -> ArtistDTO | None:
        cid = service_id.strip()
        if not _CHANNEL_ID_RE.search(cid):
            raise AdapterError(ErrorKind.UNKNOWN, f"Некорректный id артиста {service_id!r}, ожидается 'UC...'")
        try:
            with _translate_errors():
                data = self._yt.get_artist(cid)
        except AdapterError as e:
            if e.kind is ErrorKind.UNAVAILABLE:
                return None
            raise
        return _to_artist(data, channel_id=cid)

    def get_playlist(self, service_id: str) -> PlaylistDTO | None:
        pid = service_id.strip().removeprefix("VL")
        if not pid:
            raise AdapterError(ErrorKind.UNKNOWN, "Пустой id плейлиста")
        try:
            with _translate_errors():
                data = self._yt.get_playlist(pid, limit=self._playlist_limit)
        except AdapterError as e:
            if e.kind is ErrorKind.UNAVAILABLE:
                return None
            raise
        items = [t for t in (data or {}).get("tracks") or [] if isinstance(t, dict)]
        tracks = tuple(d for i in items if (d := _to_track(i)))
        return _to_playlist(data, tracks=tracks, playlist_id=pid)

    @classmethod
    def create_from_credentials(
        cls,
        token: str | None = None,
        extra_data: str | None = None,
    ) -> BaseMusicAdapter | None:
        if not token and not extra_data:
            return None
        try:
            auth_val: Any = None
            if token:
                try:
                    auth_val = json.loads(token)
                except Exception:
                    auth_val = token
            elif extra_data:
                try:
                    auth_val = json.loads(extra_data)
                except Exception:
                    auth_val = extra_data
            return cls(auth=auth_val)
        except Exception as e:
            log.warning("Failed to initialize user YouTube adapter: %s", e)
            return None

    def get_user_playlists(
        self,
        account_id: str | None = None,
        limit: int = 50,
    ) -> list[PlaylistDTO]:
        with _translate_errors():
            try:
                items = self._yt.get_library_playlists(limit=limit) or []
                return [p_dto for i in items if (p_dto := _to_playlist(i)) is not None]
            except Exception as e:
                log.warning("Failed to fetch YouTube playlists: %s", e)
                return []

    def get_user_favorites(
        self,
        account_id: str | None = None,
        limit: int = 50,
    ) -> list[TrackDTO]:
        with _translate_errors():
            try:
                liked = self._yt.get_liked_songs(limit=limit) or {}
                items = liked.get("tracks") or []
                return [t_dto for i in items if (t_dto := _to_track(i)) is not None][:limit]
            except Exception as e:
                log.warning("Failed to fetch YouTube favorites: %s", e)
                return []

    def set_track_like(
        self,
        service_id: str,
        liked: bool,
    ) -> bool:
        with _translate_errors():
            try:
                rating = LikeStatus.LIKE if liked else LikeStatus.INDIFFERENT
                self._yt.rate_song(service_id, rating=rating)
                return True
            except Exception as e:
                log.warning("Failed to sync YouTube like: %s", e)
                return False
