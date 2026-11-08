from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, UniqueConstraint, func
from sqlmodel import Field, SQLModel


class FavoriteTrack(SQLModel, table=True):
    __tablename__ = "favorite_tracks"  # type: ignore
    __table_args__ = (
        UniqueConstraint("user_id", "service", "service_id", name="uq_user_service_track"),
    )

    id: int | None = Field(default=None, primary_key=True, index=True)
    user_id: int = Field(foreign_key="users.id", index=True, nullable=False)
    service: str = Field(max_length=30, nullable=False)
    service_id: str = Field(max_length=255, nullable=False)
    title: str = Field(max_length=255, nullable=False)
    artist: str = Field(default="", max_length=255, nullable=False)
    album: str | None = Field(default=None, max_length=255)
    cover_url: str | None = Field(default=None, max_length=500)
    duration: int = Field(default=0, nullable=False)
    sources: str = Field(default="[]", max_length=255, nullable=False)  # JSON-encoded array of service codes
    playback_kind: str | None = Field(default=None, max_length=50)
    playback_ref: str | None = Field(default=None, max_length=500)
    is_edited: bool = Field(default=False, nullable=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )


class FavoriteAlbum(SQLModel, table=True):
    __tablename__ = "favorite_albums"  # type: ignore
    __table_args__ = (
        UniqueConstraint("user_id", "service", "service_id", name="uq_user_service_album"),
    )

    id: int | None = Field(default=None, primary_key=True, index=True)
    user_id: int = Field(foreign_key="users.id", index=True, nullable=False)
    service: str = Field(max_length=30, nullable=False)
    service_id: str = Field(max_length=255, nullable=False)
    title: str = Field(max_length=255, nullable=False)
    subtitle: str | None = Field(default=None, max_length=255)
    cover_url: str | None = Field(default=None, max_length=500)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )
