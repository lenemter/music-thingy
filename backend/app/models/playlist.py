from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, func
from sqlmodel import Field, SQLModel


class Playlist(SQLModel, table=True):
    __tablename__ = "playlists"  # type: ignore

    id: int | None = Field(default=None, primary_key=True, index=True)
    user_id: int = Field(foreign_key="users.id", index=True, nullable=False)
    name: str = Field(max_length=120, nullable=False)
    description: str | None = Field(default=None, max_length=500)
    cover_url: str | None = Field(default=None, max_length=500)
    is_public: bool = Field(default=False, nullable=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
    )


class PlaylistTrack(SQLModel, table=True):
    __tablename__ = "playlist_tracks"  # type: ignore

    id: int | None = Field(default=None, primary_key=True, index=True)
    playlist_id: int = Field(foreign_key="playlists.id", index=True, nullable=False)
    service: str = Field(max_length=30, nullable=False)
    service_id: str = Field(max_length=255, nullable=False)
    title: str = Field(max_length=255, nullable=False)
    artist: str = Field(default="", max_length=255, nullable=False)
    album: str | None = Field(default=None, max_length=255)
    cover_url: str | None = Field(default=None, max_length=500)
    duration: int = Field(default=0, nullable=False)
    position: int = Field(default=0, nullable=False)
    playback_kind: str | None = Field(default=None, max_length=50)
    playback_ref: str | None = Field(default=None, max_length=500)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )
