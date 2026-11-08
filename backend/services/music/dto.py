from enum import Enum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class PlaybackKind(str, Enum):
    YOUTUBE_IFRAME = "youtube_iframe"        # ref: videoId
    SOUNDCLOUD_WIDGET = "soundcloud_widget"  # ref: permalink_url
    SPOTIFY_SDK = "spotify_sdk"              # ref: spotify:track:...
    YANDEX_IFRAME = "yandex_iframe"          # ref: "{track_id}/{album_id}"


class Service(str, Enum):
    YOUTUBE = "youtube"
    SOUNDCLOUD = "soundcloud"
    SPOTIFY = "spotify"
    YANDEX = "yandex"


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
    is_playable: bool

    artist_ids: tuple[str, ...] = ()
    duration_ms: int | None = Field(default=None, ge=0)
    album: str | None = None
    isrc: str | None = None

    playback: PlaybackDTO | None = None
    direct_audio_url: HttpUrl | None = None
    external_url: HttpUrl | None = None
    artwork_url: HttpUrl | None = None

    @model_validator(mode="after")
    def _artist_ids_match_artists(self) -> Self:
        if self.artist_ids and len(self.artist_ids) != len(self.artists):
            raise ValueError("artist_ids и artists должны быть одной длины")
        return self

    @property
    def artist_display(self) -> str:
        return ", ".join(self.artists)


class ArtistDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    service: Service
    service_id: str
    name: str

    genres: tuple[str, ...] = ()
    artwork_url: HttpUrl | None = None
    external_url: HttpUrl | None = None


class PlaylistDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    service: Service
    service_id: str
    title: str

    description: str | None = None
    owner_name: str | None = None
    tracks_count: int | None = None
    artwork_url: HttpUrl | None = None
    external_url: HttpUrl | None = None

    tracks: tuple[TrackDTO, ...] | None = None


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
    PLAYLIST = "playlist"


class SearchResultDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    query: str
    tracks: tuple[TrackDTO, ...] = ()
    artists: tuple[ArtistDTO, ...] = ()
    playlists: tuple[PlaylistDTO, ...] = ()
    errors: tuple[ServiceErrorDTO, ...] = ()

