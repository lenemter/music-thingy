from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, func
from sqlmodel import Field, SQLModel


class UserUpload(SQLModel, table=True):
    __tablename__ = "user_uploads"

    id: int | None = Field(default=None, primary_key=True, index=True)
    user_id: int = Field(foreign_key="users.id", index=True, nullable=False)
    filename: str = Field(max_length=255, nullable=False)
    original_name: str = Field(max_length=255, nullable=False)
    title: str = Field(max_length=255, nullable=False)
    artist: str = Field(default="Моя музыка", max_length=255, nullable=False)
    file_type: str = Field(default="MP3", max_length=20, nullable=False)
    file_size_bytes: int = Field(default=0, nullable=False)
    duration_seconds: int = Field(default=0, nullable=False)
    cover_file: str | None = Field(default=None, max_length=255)
    cover_template: str | None = Field(default=None, max_length=100)
    is_edited: bool = Field(default=False, nullable=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
    )
