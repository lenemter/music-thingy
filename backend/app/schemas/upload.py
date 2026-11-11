from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class UserFileRead(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    name: str
    artist: str
    type: str
    duration: int
    size: float
    audio_url: str
    cover_url: str | None = None
    created_at: datetime

    # Aliases / additional fields for seamless frontend UserFile compatibility
    cover: str | None = None
    audioUrl: str | None = Field(default=None, alias="audioUrl")
    is_edited: bool = False
    isEdited: bool = Field(default=False, alias="isEdited")


class TrackEditRequest(BaseModel):
    title: str | None = None
    name: str | None = None
    artist: str | None = None


class CoverUpdateRequest(BaseModel):
    cover: str | None = None
