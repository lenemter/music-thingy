from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, UniqueConstraint, func
from sqlmodel import Field, SQLModel


class UserServiceAccount(SQLModel, table=True):
    __tablename__ = "user_service_accounts"
    __table_args__ = (
        UniqueConstraint("user_id", "service", name="uq_user_service"),
    )

    id: int | None = Field(default=None, primary_key=True, index=True)
    user_id: int = Field(foreign_key="users.id", index=True, nullable=False)
    service: str = Field(index=True, nullable=False)  # "yandex", "youtube", "vk"
    is_active: bool = Field(default=True, nullable=False)
    token: str | None = Field(default=None, nullable=True)
    refresh_token: str | None = Field(default=None, nullable=True)
    extra_data: str | None = Field(default=None, nullable=True)  # JSON string with extra settings/credentials
    account_name: str | None = Field(default=None, nullable=True)
    account_id: str | None = Field(default=None, nullable=True)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
        ),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            onupdate=func.now(),
            nullable=False,
        ),
    )
