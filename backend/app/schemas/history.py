from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel


class ListeningHistoryCreate(BaseModel):
    service: str
    service_id: str
    title: str
    artist: str = ""
    album: str | None = None
    cover_url: str | None = None
    duration: int = 0


class ListeningHistoryRead(BaseModel):
    id: int
    service: str
    service_id: str
    title: str
    artist: str
    album: str | None = None
    cover: str
    duration: int
    listened_at: datetime
