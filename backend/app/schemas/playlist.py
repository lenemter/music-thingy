from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class PlaylistTrackAdd(BaseModel):
    service: str
    service_id: str
    title: str
    artist: str = ""
    album: str | None = None
    cover_url: str | None = None
    duration: int = 0
    playback_kind: str | None = None
    playback_ref: str | None = None


class PlaylistTrackRead(BaseModel):
    id: int
    playlist_id: int
    service: str
    service_id: str
    title: str
    artist: str
    album: str | None = None
    cover: str
    duration: int
    position: int
    playback_kind: str | None = None
    playback_ref: str | None = None
    created_at: datetime


class PlaylistCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    cover_url: str | None = None
    is_public: bool = False


class PlaylistUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    cover_url: str | None = None
    is_public: bool | None = None


class PlaylistReorder(BaseModel):
    track_ids: list[int]  # Ordered list of PlaylistTrack.id


class PlaylistRead(BaseModel):
    id: int
    name: str
    description: str | None = None
    cover: str
    tracks_count: int = 0
    is_public: bool = False
    tracks: list[PlaylistTrackRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
