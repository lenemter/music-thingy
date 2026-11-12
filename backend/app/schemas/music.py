from __future__ import annotations

from pydantic import BaseModel


class PlaybackInfo(BaseModel):
    kind: str
    ref: str
    direct_audio_url: str | None = None


class TrackRead(BaseModel):
    id: int
    track_key: str
    service: str
    service_id: str
    title: str
    artist: str
    artists: list[str] = []
    artist_ids: list[str] = []
    album: str | None = None
    cover: str = ""
    artwork_url: str | None = None
    duration: int = 0
    duration_ms: int | None = None
    sources: list[str] = []
    source: str
    is_playable: bool = True
    edited: bool = False
    liked: bool = False
    playback: PlaybackInfo | None = None
    direct_audio_url: str | None = None
    stream_url: str | None = None
    external_url: str | None = None


class LikeRequest(BaseModel):
    title: str | None = None
    artist: str | None = None
    cover: str | None = None
    duration: int | None = None


class LikeResponse(TrackRead):
    synced: bool = True


class AlbumRead(BaseModel):
    id: int
    service: str
    service_id: str
    title: str
    subtitle: str
    artist: str | None = None
    year: int | None = None
    cover: str = ""
    artwork_url: str | None = None
    external_url: str | None = None
    tracks_count: int | None = None
    tracks: list[TrackRead] | None = None


class ArtistRead(BaseModel):
    service: str
    service_id: str
    name: str
    genres: list[str] = []
    cover: str | None = None
    artwork_url: str | None = None
    external_url: str | None = None


class PlaylistRead(BaseModel):
    id: int
    service: str
    service_id: str
    name: str
    title: str
    cover: str = ""
    artwork_url: str | None = None
    description: str | None = None
    owner_name: str | None = None
    tracks_count: int | None = None
    external_url: str | None = None
    tracks: list[TrackRead] | None = None


class ServiceErrorRead(BaseModel):
    service: str
    kind: str
    message: str
    status_code: int | None = None


class MusicSearchResponse(BaseModel):
    query: str
    tracks: list[TrackRead] = []
    albums: list[AlbumRead] = []
    artists: list[ArtistRead] = []
    playlists: list[PlaylistRead] = []
    errors: list[ServiceErrorRead] = []
