from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.deps import get_current_active_user
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.database import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, RefreshTokenRequest, Token
from app.schemas.user import UserCreate, UserRead

router = APIRouter(prefix="/api/auth", tags=["auth"])


async def _authenticate_and_create_tokens(identifier: str, password: str, db: AsyncSession) -> Token:
    statement = select(User).where(User.email == identifier.strip().lower())
    result = await db.exec(statement)
    user = result.first()

    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No active account found with the given credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is inactive",
        )

    assert user.id is not None
    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        access=access_token,
        refresh=refresh_token,
        token_type="bearer",
    )


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
@router.post("/register/", response_model=UserRead, status_code=status.HTTP_201_CREATED, include_in_schema=False)
async def register(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> User:
    email_clean = user_in.email.strip().lower()
    statement = select(User).where(User.email == email_clean)
    result = await db.exec(statement)
    existing_user = result.first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists.",
        )

    new_user = User(
        email=email_clean,
        hashed_password=hash_password(user_in.password),
        display_name=user_in.display_name.strip() if user_in.display_name else "",
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


@router.post("/token", response_model=Token)
@router.post("/token/", response_model=Token, include_in_schema=False)
@router.post("/login", response_model=Token)
@router.post("/login/", response_model=Token, include_in_schema=False)
async def login(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Token:
    content_type = request.headers.get("content-type", "")

    identifier: str | None = None
    password: str | None = None

    if "application/json" in content_type:
        try:
            body = await request.json()
            login_req = LoginRequest(**body)
            identifier = login_req.get_identifier()
            password = login_req.password
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid request body: {str(e)}",
            )
    else:
        form = await request.form()
        raw_ident = form.get("username") or form.get("email")
        raw_pass = form.get("password")
        identifier = str(raw_ident) if raw_ident is not None else None
        password = str(raw_pass) if raw_pass is not None else None

    if not identifier or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email/username and password are required",
        )

    return await _authenticate_and_create_tokens(identifier, password, db)


@router.post("/token/refresh", response_model=Token)
@router.post("/token/refresh/", response_model=Token, include_in_schema=False)
async def refresh_token(
    refresh_req: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> Token:
    token_str = refresh_req.get_token()
    payload = decode_token(token_str)

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type: refresh token expected",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = int(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    statement = select(User).where(User.id == user_id)
    result = await db.exec(statement)
    user = result.first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    assert user.id is not None
    access_token = create_access_token(user.id)
    new_refresh_token = create_refresh_token(user.id)

    return Token(
        access_token=access_token,
        refresh_token=new_refresh_token,
        access=access_token,
        refresh=new_refresh_token,
        token_type="bearer",
    )


@router.get("/me", response_model=UserRead)
@router.get("/me/", response_model=UserRead, include_in_schema=False)
async def get_me(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    return current_user
