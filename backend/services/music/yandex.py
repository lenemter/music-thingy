"""Адаптер Яндекс Музыки на базе неофициальной библиотеки yandex-music.

Форматы service_id:
    трек      "{track_id}:{album_id}" или "{track_id}"
    артист    "{artist_id}"
    плейлист  "{owner_uid}:{kind}"
    альбом    "{album_id}"
"""
import logging
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any, ClassVar

from yandex_music import Client
from yandex_music.exceptions import (
    BadRequestError,
    NetworkError,
    NotFoundError,
    TimedOutError,
    UnauthorizedError,
    YandexMusicError,
)
from yandex_music.utils.request import Request

from .base import AdapterError, BaseMusicAdapter
from .dto import (
    AlbumDTO,
    ArtistDTO,
    ErrorKind,
    PlaybackDTO,
    PlaybackKind,
    PlaylistDTO,
    SearchResultDTO,
    SearchType,
    Service,
    TrackDTO,
)

log = logging.getLogger(__name__)

_WEB_URL = "https://music.yandex.ru"


@contextmanager
def _translate_errors() -> Iterator[None]:
    try:
        yield
    except UnauthorizedError as e:
        raise AdapterError(ErrorKind.AUTH_FAILED, str(e), 401) from e
    except TimedOutError as e:
        raise AdapterError(ErrorKind.TIMEOUT, str(e)) from e
    except NotFoundError as e:
        raise AdapterError(ErrorKind.UNAVAILABLE, str(e), 404) from e
    except BadRequestError as e:
        raise AdapterError(ErrorKind.UNKNOWN, str(e), 400) from e
    except NetworkError as e:
        raise AdapterError(ErrorKind.UNAVAILABLE, str(e)) from e
    except YandexMusicError as e:
        raise AdapterError(ErrorKind.UNKNOWN, str(e)) from e


def _cover_url(entity: Any, size: str = "400x400") -> str | None:
    uri = (
        getattr(entity, "cover_uri", None)
        or getattr(getattr(entity, "cover", None), "uri", None)
        or getattr(entity, "og_image", None)
    )
    if not uri:
        return None
    uri = uri.replace("%%", size)
    return uri if uri.startswith("http") else f"https://{uri}"


def _results(block: Any) -> list[Any]:
    return list(getattr(block, "results", None) or [])


def _direct_audio_url(track: Any) -> str | None:
    """Прямая ссылка на mp3 с максимальным битрейтом."""
    try:
        infos = track.get_download_info(get_direct_links=True)
    except YandexMusicError as e:
        log.warning("Не удалось получить прямую ссылку для трека %s: %s", getattr(track, "id", None), e)
        return None
    mp3 = [i for i in infos or [] if getattr(i, "codec", None) == "mp3" and getattr(i, "direct_link", None)]
    best = max(mp3, key=lambda i: getattr(i, "bitrate_in_kbps", 0) or 0, default=None)
    return best.direct_link if best else None


def _to_track(t: Any, direct_audio_url: str | None = None) -> TrackDTO | None:
    if t is None or getattr(t, "id", None) is None or not getattr(t, "title", None):
        return None

    track_id = str(t.id)
    albums = getattr(t, "albums", None) or []
    album = albums[0] if albums else None
    album_id = str(album.id) if album is not None and getattr(album, "id", None) is not None else None

    named = [a for a in (getattr(t, "artists", None) or []) if getattr(a, "name", None)]
    artists = tuple(a.name for a in named)
    ids = tuple(str(a.id) for a in named if getattr(a, "id", None) is not None)
    artist_ids = ids if len(ids) == len(artists) else ()

    title = f"{t.title} ({t.version})" if getattr(t, "version", None) else t.title
    is_playable = bool(getattr(t, "available", False))

    playback = None
    if is_playable and album_id:
        playback = PlaybackDTO(kind=PlaybackKind.YANDEX_IFRAME, ref=f"{track_id}/{album_id}")

    return TrackDTO(
        service=Service.YANDEX,
        service_id=f"{track_id}:{album_id}" if album_id else track_id,
        title=title,
        artists=artists,
        is_playable=is_playable,
        artist_ids=artist_ids,
        duration_ms=getattr(t, "duration_ms", None),
        album=getattr(album, "title", None) if album is not None else None,
        playback=playback,
        direct_audio_url=direct_audio_url,
        external_url=f"{_WEB_URL}/album/{album_id}/track/{track_id}" if album_id else None,
        artwork_url=_cover_url(t),
        sources=("ЯМ",),
    )


def _to_artist(a: Any) -> ArtistDTO | None:
    if a is None or getattr(a, "id", None) is None or not getattr(a, "name", None):
        return None
    return ArtistDTO(
        service=Service.YANDEX,
        service_id=str(a.id),
        name=a.name,
        genres=tuple(getattr(a, "genres", None) or ()),
        artwork_url=_cover_url(a),
        external_url=f"{_WEB_URL}/artist/{a.id}",
    )


def _to_album(alb: Any) -> AlbumDTO | None:
    if alb is None or getattr(alb, "id", None) is None or not getattr(alb, "title", None):
        return None
    artist_names = [a.name for a in (getattr(alb, "artists", None) or []) if getattr(a, "name", None)]
    artist_display = ", ".join(artist_names) if artist_names else None
    return AlbumDTO(
        service=Service.YANDEX,
        service_id=str(alb.id),
        title=alb.title,
        subtitle=f"{artist_display} · альбом" if artist_display else "Альбом",
        artist=artist_display,
        year=getattr(alb, "year", None),
        tracks_count=getattr(alb, "track_count", None),
        artwork_url=_cover_url(alb),
        external_url=f"{_WEB_URL}/album/{alb.id}",
    )


def _to_playlist(p: Any, tracks: tuple[TrackDTO, ...] | None = None) -> PlaylistDTO | None:
    if p is None or getattr(p, "uid", None) is None or getattr(p, "kind", None) is None or not getattr(p, "title", None):
        return None
    owner = getattr(p, "owner", None)
    owner_login = getattr(owner, "login", None)
    return PlaylistDTO(
        service=Service.YANDEX,
        service_id=f"{p.uid}:{p.kind}",
        title=p.title,
        description=getattr(p, "description", None) or None,
        owner_name=(getattr(owner, "name", None) or owner_login) if owner else None,
        tracks_count=getattr(p, "track_count", None),
        artwork_url=_cover_url(p),
        external_url=(f"{_WEB_URL}/users/{owner_login}/playlists/{p.kind}" if owner_login else None),
        tracks=tracks,
    )


class YandexMusicAdapter(BaseMusicAdapter):
    service: ClassVar[Service] = Service.YANDEX
    official: ClassVar[bool] = False

    def __init__(self, token: str | None = None, *, request: Request | None = None) -> None:
        with _translate_errors():
            self._client = Client(token, request=request).init()

    def search(
        self,
        query: str,
        types: frozenset[SearchType] = frozenset({SearchType.TRACK}),
        limit: int = 10,
    ) -> SearchResultDTO:
        type_ = next(iter(types)).value if len(types) == 1 else "all"
        with _translate_errors():
            res = self._client.search(query, type_=type_)

        tracks: tuple[TrackDTO, ...] = ()
        artists: tuple[ArtistDTO, ...] = ()
        albums: tuple[AlbumDTO, ...] = ()
        playlists: tuple[PlaylistDTO, ...] = ()

        if res is not None:
            if SearchType.TRACK in types:
                tracks = tuple(d for t in _results(getattr(res, "tracks", None))[:limit] if (d := _to_track(t)))
            if SearchType.ARTIST in types:
                artists = tuple(d for a in _results(getattr(res, "artists", None))[:limit] if (d := _to_artist(a)))
            if SearchType.ALBUM in types:
                albums = tuple(d for alb in _results(getattr(res, "albums", None))[:limit] if (d := _to_album(alb)))
            if SearchType.PLAYLIST in types:
                playlists = tuple(d for p in _results(getattr(res, "playlists", None))[:limit] if (d := _to_playlist(p)))

        return SearchResultDTO(
            query=query,
            tracks=tracks,
            artists=artists,
            albums=albums,
            playlists=playlists,
        )

    def get_track(self, service_id: str) -> TrackDTO | None:
        actual_id = service_id.split(":")[0]
        with _translate_errors():
            try:
                found = self._client.tracks([actual_id])
            except NotFoundError:
                return None
        if not found:
            return None
        track = found[0]
        url = _direct_audio_url(track) if getattr(track, "available", False) else None
        return _to_track(track, direct_audio_url=url)

    def get_artist(self, service_id: str) -> ArtistDTO | None:
        with _translate_errors():
            try:
                found = self._client.artists([service_id])
            except (NotFoundError, BadRequestError):
                return None
        return _to_artist(found[0]) if found else None

    def get_album(self, service_id: str) -> AlbumDTO | None:
        with _translate_errors():
            try:
                found = self._client.albums([service_id])
            except (NotFoundError, BadRequestError):
                return None
        return _to_album(found[0]) if found else None

    def _resolve_tracks(self, items: list[Any]) -> list[Any]:
        """Догружает полные Track для TrackShort"""
        short = [t for t in items if not hasattr(t, "title")]
        if not short:
            return items
        ids = [f"{t.id}:{t.album_id}" if getattr(t, "album_id", None) else str(t.id) for t in short]
        fetched: dict[str, Any] = {}
        for i in range(0, len(ids), 100):
            for t in self._client.tracks(ids[i:i + 100]) or []:
                fetched[str(t.id)] = t
        return [t if hasattr(t, "title") else fetched.get(str(t.id)) for t in items]

    def get_playlist(self, service_id: str) -> PlaylistDTO | None:
        uid, _, kind = service_id.partition(":")
        if not uid or not kind:
            raise AdapterError(
                ErrorKind.UNKNOWN,
                f"Некорректный id плейлиста {service_id!r}, ожидается 'owner_uid:kind'",
            )

        with _translate_errors():
            try:
                playlist = self._client.users_playlists(kind, user_id=uid)
            except NotFoundError:
                return None
            if isinstance(playlist, list):
                playlist = playlist[0] if playlist else None
            if playlist is None:
                return None
            full_tracks = self._resolve_tracks(playlist.fetch_tracks() or [])

        tracks = tuple(d for t in full_tracks if (d := _to_track(t)))
        return _to_playlist(playlist, tracks=tracks)
