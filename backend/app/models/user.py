from datetime import datetime, timezone
from pydantic import EmailStr
from sqlalchemy import Column, DateTime, func
from sqlmodel import Field, SQLModel


class UserBase(SQLModel):
    email: EmailStr = Field(
        unique=True,
        index=True,
        max_length=255,
        nullable=False,
    )
    display_name: str = Field(
        default="",
        max_length=50,
        nullable=False,
    )


class User(UserBase, table=True):
    __tablename__ = "users"  # type: ignore

    id: int | None = Field(default=None, primary_key=True, index=True)
    hashed_password: str = Field(max_length=255, nullable=False)
    is_active: bool = Field(default=True, nullable=False)
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

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"
