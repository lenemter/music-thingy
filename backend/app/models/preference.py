from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, UniqueConstraint, func
from sqlmodel import Field, SQLModel


class UserServicePreference(SQLModel, table=True):
    __tablename__ = "user_service_preferences"  # type: ignore
    __table_args__ = (
        UniqueConstraint("user_id", "service", name="uq_user_service_pref"),
    )

    id: int | None = Field(default=None, primary_key=True, index=True)
    user_id: int = Field(foreign_key="users.id", index=True, nullable=False)
    service: str = Field(max_length=30, nullable=False)
    is_enabled: bool = Field(default=True, nullable=False)
    api_token: str | None = Field(default=None, max_length=500)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
    )
