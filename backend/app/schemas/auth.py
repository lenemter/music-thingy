from pydantic import EmailStr
from sqlmodel import SQLModel


class Token(SQLModel):
    access_token: str
    refresh_token: str
    access: str
    refresh: str
    token_type: str = "bearer"


class LoginRequest(SQLModel):
    email: EmailStr | None = None
    username: str | None = None
    password: str

    def get_identifier(self) -> str:
        ident = self.email or self.username
        if not ident:
            raise ValueError("Email or username is required")
        return str(ident)


class RefreshTokenRequest(SQLModel):
    refresh: str | None = None
    refresh_token: str | None = None

    def get_token(self) -> str:
        token = self.refresh or self.refresh_token
        if not token:
            raise ValueError("Refresh token is required")
        return token
