from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class TrackRef(BaseModel):
    service: str = Field(..., min_length=1, max_length=50)
    service_id: str = Field(..., min_length=1, max_length=255)
    title: str | None = None
    artist: str | None = None
    cover: str | None = None
    duration: int | None = Field(default=None, ge=0)


class PlaylistCreateRequest(BaseModel):
    name: str
    tracks: list[TrackRef] = Field(default_factory=list)


class PlaylistUpdateRequest(BaseModel):
    name: str


class UserPlaylistRead(BaseModel):
    id: int
    name: str
    tracks_count: int = 0
    duration: int = 0
    covers: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
