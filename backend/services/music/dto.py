from __future__ import annotations

from enum import Enum
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class PlaybackKind(str, Enum):
    YOUTUBE_IFRAME = "youtube_iframe"        # ref: videoId
    SOUNDCLOUD_WIDGET = "soundcloud_widget"  # ref: permalink_url
    SPOTIFY_SDK = "spotify_sdk"              # ref: spotify:track:... or uri
    YANDEX_IFRAME = "yandex_iframe"          # ref: "{track_id}/{album_id}"
    AUDIO_STREAM = "audio_stream"            # direct audio or local stream endpoint
    DIRECT_URL = "direct_url"                # direct web url to mp3/audio


class Service(str, Enum):
    YOUTUBE = "youtube"
    SOUNDCLOUD = "soundcloud"
    SPOTIFY = "spotify"
    YANDEX = "yandex"
    LOCAL = "local"


SERVICE_CODE_MAP: dict[Service, str] = {
    Service.YANDEX: "ЯМ",
    Service.SPOTIFY: "SP",
    Service.SOUNDCLOUD: "SC",
    Service.YOUTUBE: "YT",
    Service.LOCAL: "ФАЙЛ",
}

SERVICE_NAME_MAP: dict[Service, str] = {
    Service.YANDEX: "Яндекс Музыка",
    Service.SPOTIFY: "Spotify",
    Service.SOUNDCLOUD: "SoundCloud",
    Service.YOUTUBE: "YouTube",
    Service.LOCAL: "Моя музыка",
}

CODE_TO_SERVICE_MAP: dict[str, Service] = {
    "ЯМ": Service.YANDEX,
    "SP": Service.SPOTIFY,
    "SC": Service.SOUNDCLOUD,
    "YT": Service.YOUTUBE,
    "ФАЙЛ": Service.LOCAL,
    "yandex": Service.YANDEX,
    "spotify": Service.SPOTIFY,
    "soundcloud": Service.SOUNDCLOUD,
    "youtube": Service.YOUTUBE,
    "local": Service.LOCAL,
}


class PlaybackDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: PlaybackKind
    ref: str


class TrackDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    service: Service
    service_id: str
    title: str
    artists: tuple[str, ...]
    is_playable: bool = True

    artist_ids: tuple[str, ...] = ()
    duration_ms: int | None = Field(default=None, ge=0)
    album: str | None = None
    isrc: str | None = None

    playback: PlaybackDTO | None = None
    direct_audio_url: str | None = None
    external_url: str | None = None
    artwork_url: str | None = None

    sources: tuple[str, ...] = ()  # Service codes, e.g. ("ЯМ", "SP")
    edited: bool = False
    liked: bool = False

    @model_validator(mode="after")
    def _artist_ids_match_artists(self) -> Self:
        if self.artist_ids and len(self.artist_ids) != len(self.artists):
            raise ValueError("artist_ids and artists must have the same length")
        return self

    @property
    def artist_display(self) -> str:
        return ", ".join(self.artists) if self.artists else "Неизвестный исполнитель"

    @property
    def duration_seconds(self) -> int:
        if self.duration_ms:
            return max(1, self.duration_ms // 1000)
        return 0

    def to_frontend_dict(self, numeric_id: int | None = None) -> dict[str, Any]:
        """Maps TrackDTO to the exact schema frontend expects in `Track`."""
        source_code = SERVICE_CODE_MAP.get(self.service, str(self.service.value).upper()[:2])
        all_sources = list(self.sources) if self.sources else [source_code]

        # Generate a stable positive integer id if numeric_id is not passed
        track_key = f"{self.service.value}:{self.service_id}"
        stable_id = numeric_id if numeric_id is not None else (abs(hash(track_key)) % 10_000_000 + 1)

        return {
            "id": stable_id,
            "track_key": track_key,
            "service": self.service.value,
            "service_id": self.service_id,
            "title": self.title,
            "artist": self.artist_display,
            "cover": str(self.artwork_url) if self.artwork_url else "",
            "duration": self.duration_seconds,
            "sources": all_sources,
            "source": source_code,
            "edited": self.edited,
            "liked": self.liked,
            "playback": self.playback.model_dump() if self.playback else None,
            "direct_audio_url": str(self.direct_audio_url) if self.direct_audio_url else None,
            "external_url": str(self.external_url) if self.external_url else None,
        }


class ArtistDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    service: Service
    service_id: str
    name: str

    genres: tuple[str, ...] = ()
    artwork_url: str | None = None
    external_url: str | None = None


class AlbumDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    service: Service
    service_id: str
    title: str
    subtitle: str | None = None
    artist: str | None = None
    year: int | None = None
    tracks_count: int | None = None
    artwork_url: str | None = None
    external_url: str | None = None

    def to_frontend_dict(self, numeric_id: int | None = None) -> dict[str, Any]:
        album_key = f"{self.service.value}:{self.service_id}"
        stable_id = numeric_id if numeric_id is not None else (abs(hash(album_key)) % 10_000_000 + 1)
        sub = self.subtitle or (f"{self.artist} · альбом" if self.artist else "Альбом")
        return {
            "id": stable_id,
            "service": self.service.value,
            "service_id": self.service_id,
            "title": self.title,
            "subtitle": sub,
            "cover": str(self.artwork_url) if self.artwork_url else "",
        }


class PlaylistDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    service: Service
    service_id: str
    title: str

    description: str | None = None
    owner_name: str | None = None
    tracks_count: int | None = None
    artwork_url: str | None = None
    external_url: str | None = None

    tracks: tuple[TrackDTO, ...] | None = None

    def to_frontend_dict(self, numeric_id: int | None = None) -> dict[str, Any]:
        playlist_key = f"{self.service.value}:{self.service_id}"
        stable_id = numeric_id if numeric_id is not None else (abs(hash(playlist_key)) % 10_000_000 + 1)
        return {
            "id": stable_id,
            "name": self.title,
            "cover": str(self.artwork_url) if self.artwork_url else "",
            "description": self.description,
            "tracks_count": self.tracks_count or (len(self.tracks) if self.tracks else 0),
        }


class ErrorKind(str, Enum):
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    QUOTA_EXCEEDED = "quota_exceeded"
    AUTH_FAILED = "auth_failed"
    NOT_SUPPORTED = "not_supported"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


class ServiceErrorDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    service: Service
    kind: ErrorKind
    message: str
    status_code: int | None = None


class SearchType(str, Enum):
    TRACK = "track"
    ARTIST = "artist"
    ALBUM = "album"
    PLAYLIST = "playlist"


class SearchResultDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    query: str
    tracks: tuple[TrackDTO, ...] = ()
    artists: tuple[ArtistDTO, ...] = ()
    albums: tuple[AlbumDTO, ...] = ()
    playlists: tuple[PlaylistDTO, ...] = ()
    errors: tuple[ServiceErrorDTO, ...] = ()
