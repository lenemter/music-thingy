from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class FavoriteTrackCreate(BaseModel):
    service: str
    service_id: str
    title: str
    artist: str = ""
    album: str | None = None
    cover_url: str | None = None
    duration: int = 0
    sources: list[str] = Field(default_factory=list)
    playback_kind: str | None = None
    playback_ref: str | None = None
    is_edited: bool = False


class FavoriteTrackRead(BaseModel):
    id: int
    service: str
    service_id: str
    title: str
    artist: str
    album: str | None = None
    cover: str
    duration: int
    sources: list[str] = Field(default_factory=list)
    source: str
    is_edited: bool = False
    liked: bool = True
    playback_kind: str | None = None
    playback_ref: str | None = None
    created_at: datetime


class FavoriteAlbumCreate(BaseModel):
    service: str
    service_id: str
    title: str
    subtitle: str | None = None
    cover_url: str | None = None


class FavoriteAlbumRead(BaseModel):
    id: int
    service: str
    service_id: str
    title: str
    subtitle: str
    cover: str
    created_at: datetime
