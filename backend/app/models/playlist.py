from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, UniqueConstraint, func
from sqlmodel import Field, SQLModel


class UserPlaylist(SQLModel, table=True):
    __tablename__ = "user_playlists"

    id: int | None = Field(default=None, primary_key=True, index=True)
    user_id: int = Field(foreign_key="users.id", index=True, nullable=False)
    name: str = Field(max_length=255, nullable=False)
    normalized_name: str = Field(max_length=255, index=True, nullable=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
    )


class UserPlaylistTrack(SQLModel, table=True):
    __tablename__ = "user_playlist_tracks"
    __table_args__ = (
        UniqueConstraint("playlist_id", "service", "service_id", name="uq_user_playlist_tracks_item"),
    )

    id: int | None = Field(default=None, primary_key=True, index=True)
    playlist_id: int = Field(foreign_key="user_playlists.id", index=True, nullable=False)
    position: int = Field(default=0, nullable=False)
    service: str = Field(max_length=50, index=True, nullable=False)
    service_id: str = Field(max_length=255, index=True, nullable=False)
    title: str = Field(default="", max_length=255, nullable=False)
    artist: str = Field(default="", max_length=255, nullable=False)
    cover: str | None = Field(default=None, max_length=1000)
    duration: int = Field(default=0, nullable=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )
