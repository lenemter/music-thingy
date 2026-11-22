from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, UniqueConstraint, func
from sqlmodel import Field, SQLModel


class UserLike(SQLModel, table=True):
    __tablename__ = "user_likes"
    __table_args__ = (
        UniqueConstraint("user_id", "service", "service_id", name="uq_user_likes_track"),
    )

    id: int | None = Field(default=None, primary_key=True, index=True)
    user_id: int = Field(foreign_key="users.id", index=True, nullable=False)
    service: str = Field(max_length=50, index=True, nullable=False)
    service_id: str = Field(max_length=255, index=True, nullable=False)
    title: str = Field(default="", max_length=255, nullable=False)
    artist: str = Field(default="", max_length=255, nullable=False)
    cover: str | None = Field(default=None, max_length=1000)
    duration: int = Field(default=0, nullable=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )
