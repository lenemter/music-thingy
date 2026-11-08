from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class PlaybackInfo(BaseModel):
    kind: str
    ref: str


class TrackRead(BaseModel):
    id: int
    track_key: str | None = None
    service: str
    service_id: str
    title: str
    artist: str
    cover: str
    duration: int
    sources: list[str] = Field(default_factory=list)
    source: str
    edited: bool = False
    liked: bool = False
    playback: PlaybackInfo | None = None
    direct_audio_url: str | None = None
    external_url: str | None = None


class AlbumRead(BaseModel):
    id: int
    service: str
    service_id: str
    title: str
    subtitle: str
    cover: str


class ArtistRead(BaseModel):
    service: str
    service_id: str
    name: str
    genres: list[str] = Field(default_factory=list)
    cover: str | None = None
    external_url: str | None = None


class PlaylistSearchResult(BaseModel):
    id: int
    service: str
    service_id: str
    name: str
    cover: str
    description: str | None = None
    tracks_count: int = 0


class MusicSearchResponse(BaseModel):
    query: str
    tracks: list[TrackRead] = Field(default_factory=list)
    albums: list[AlbumRead] = Field(default_factory=list)
    artists: list[ArtistRead] = Field(default_factory=list)
    playlists: list[PlaylistSearchResult] = Field(default_factory=list)
    errors: list[dict[str, Any]] = Field(default_factory=list)


class WaveRead(BaseModel):
    date: str
    title: str
    description: str
    trackCount: int
    duration: int
    tracks: list[TrackRead] = Field(default_factory=list)
