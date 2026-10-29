from datetime import datetime
from sqlmodel import Field, SQLModel

from app.models.user import UserBase


class UserCreate(UserBase):
    password: str = Field(min_length=8, description="Password must be at least 8 characters long")


class UserRead(UserBase):
    id: int
    is_active: bool
    created_at: datetime
