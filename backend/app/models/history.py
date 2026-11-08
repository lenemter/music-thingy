from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, func
from sqlmodel import Field, SQLModel


class ListeningHistory(SQLModel, table=True):
    __tablename__ = "listening_history"  # type: ignore

    id: int | None = Field(default=None, primary_key=True, index=True)
    user_id: int = Field(foreign_key="users.id", index=True, nullable=False)
    service: str = Field(max_length=30, nullable=False)
    service_id: str = Field(max_length=255, nullable=False)
    title: str = Field(max_length=255, nullable=False)
    artist: str = Field(default="", max_length=255, nullable=False)
    album: str | None = Field(default=None, max_length=255)
    cover_url: str | None = Field(default=None, max_length=500)
    duration: int = Field(default=0, nullable=False)
    listened_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )
