from __future__ import annotations

import json
import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from ytmusicapi import YTMusic
from ytmusicapi.auth.oauth import OAuthCredentials

from app.api.deps import get_current_user
from app.config import settings
from app.database import get_db
from app.models.service_account import UserServiceAccount
from app.models.user import User
from app.schemas.service import (
    ConnectServiceRequest,
    ServiceConnectionStatus,
    ServiceStatusRead,
    ToggleServiceRequest,
    YouTubeDeviceCodeResponse,
    YouTubePollTokenRequest,
)
from services.music.aggregator import aggregator
from services.music.dto import (
    CODE_TO_SERVICE_MAP,
    SERVICE_CODE_MAP,
    SERVICE_NAME_MAP,
    Service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/services", tags=["services"])

SUPPORTED_USER_SERVICES = [
    (Service.YANDEX, "ЯМ", "Яндекс Музыка"),
    (Service.YOUTUBE, "YT", "YouTube"),
    (Service.VK, "VK", "VK Музыка"),
]


@router.get("", response_model=list[ServiceStatusRead])
async def list_services() -> list[ServiceStatusRead]:
    """Returns the list of music source services and their online availability status."""
    statuses = aggregator.get_services_status()
    return [ServiceStatusRead(**s) for s in statuses]


@router.get("/connections", response_model=list[ServiceConnectionStatus])
async def get_user_connections(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> list[ServiceConnectionStatus]:
    """Returns account connection and activation status for each service for the current user."""
    stmt = select(UserServiceAccount).where(UserServiceAccount.user_id == current_user.id)
    res = await db.exec(stmt)
    accounts = {acc.service.lower(): acc for acc in res.all()}

    statuses: list[ServiceConnectionStatus] = []
    for s_enum, code, name in SUPPORTED_USER_SERVICES:
        acc = accounts.get(s_enum.value)
        is_connected = bool(acc and (acc.token or acc.extra_data))
        is_active = acc.is_active if acc else is_connected
        account_name = acc.account_name if acc else None
        account_id = acc.account_id if acc else None

        statuses.append(
            ServiceConnectionStatus(
                service=s_enum.value,
                code=code,
                name=name,
                connected=is_connected,
                is_active=is_active,
                account_name=account_name,
                account_id=account_id,
            )
        )

    return statuses


@router.post("/{service}/connect", response_model=ServiceConnectionStatus)
async def connect_service(
    service: str,
    req: ConnectServiceRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> ServiceConnectionStatus:
    """Connect a user account to a music service (Yandex, YouTube, or VK)."""
    s_enum = CODE_TO_SERVICE_MAP.get(service.lower())
    if not s_enum or s_enum not in (Service.YANDEX, Service.YOUTUBE, Service.VK):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported service for linking: '{service}'. Supported: yandex, youtube, vk",
        )

    account_name: str | None = None
    account_id: str | None = None
    saved_token: str | None = req.token
    saved_extra_data: str | None = None

    # 1. Yandex Music validation
    if s_enum == Service.YANDEX:
        if not req.token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token is required to connect Yandex Music",
            )
        try:
            from yandex_music import Client
            ym_client = Client(req.token).init()
            if ym_client.me and ym_client.me.account:
                account_name = ym_client.me.account.full_name or ym_client.me.account.login
                account_id = str(ym_client.me.account.uid) if ym_client.me.account.uid else None
            else:
                account_name = "Яндекс Музыка"
        except Exception as e:
            logger.warning("Yandex token validation failed: %s", e)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Недействительный токен Яндекс Музыки: {e}",
            )

    # 2. YouTube Music validation
    elif s_enum == Service.YOUTUBE:
        auth_payload = req.auth_json or req.token
        if not auth_payload and not (req.client_id and req.client_secret and req.refresh_token):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Provide 'token' / 'auth_json' or OAuth credentials to connect YouTube Music",
            )

        parsed_auth: Any = auth_payload
        if auth_payload:
            try:
                parsed_auth = json.loads(auth_payload)
            except Exception:
                parsed_auth = auth_payload

        try:
            yt = YTMusic(auth=parsed_auth)
            # Verify library access
            pls = yt.get_library_playlists(limit=1)
            account_name = "YouTube Music"
            saved_token = json.dumps(parsed_auth) if isinstance(parsed_auth, dict) else str(parsed_auth)
        except Exception as e:
            logger.warning("YouTube auth validation failed: %s", e)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Не удалось авторизоваться в YouTube Music: {e}",
            )

    # 3. VK Music validation
    elif s_enum == Service.VK:
        if not req.token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token is required to connect VK Music",
            )
        user_agent = req.user_agent or settings.VK_DEFAULT_USER_AGENT
        saved_extra_data = json.dumps({"user_agent": user_agent})
        try:
            from vkpymusic import Service as VkService
            vk_api = VkService(req.token, user_agent)
            # Quick validation
            vk_api.get_songs_by_id(["1_1"])
            account_name = "VK Музыка"
        except Exception as e:
            # Check if error is access/auth related
            from vkpymusic.vk_api import VkApiException
            if isinstance(e, VkApiException) and e.error_code in (5, 17):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Недействительный токен VK: {e}",
                )
            account_name = "VK Музыка"

    # Save or update UserServiceAccount
    stmt = select(UserServiceAccount).where(
        UserServiceAccount.user_id == current_user.id,
        UserServiceAccount.service == s_enum.value,
    )
    res = await db.exec(stmt)
    acc = res.first()

    if not acc:
        acc = UserServiceAccount(
            user_id=current_user.id or 0,
            service=s_enum.value,
            is_active=True,
            token=saved_token,
            refresh_token=req.refresh_token,
            extra_data=saved_extra_data,
            account_name=account_name,
            account_id=account_id,
        )
        db.add(acc)
    else:
        acc.token = saved_token
        acc.refresh_token = req.refresh_token or acc.refresh_token
        acc.extra_data = saved_extra_data or acc.extra_data
        acc.account_name = account_name or acc.account_name
        acc.account_id = account_id or acc.account_id
        acc.is_active = True
        db.add(acc)

    await db.commit()
    await db.refresh(acc)

    code = SERVICE_CODE_MAP.get(s_enum, s_enum.value.upper()[:2])
    name = SERVICE_NAME_MAP.get(s_enum, s_enum.value.capitalize())

    return ServiceConnectionStatus(
        service=s_enum.value,
        code=code,
        name=name,
        connected=True,
        is_active=acc.is_active,
        account_name=acc.account_name,
        account_id=acc.account_id,
    )


@router.delete("/{service}/disconnect", response_model=ServiceConnectionStatus)
async def disconnect_service(
    service: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> ServiceConnectionStatus:
    """Disconnect and remove credentials for a linked music service."""
    s_enum = CODE_TO_SERVICE_MAP.get(service.lower())
    if not s_enum:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown service: '{service}'",
        )

    stmt = select(UserServiceAccount).where(
        UserServiceAccount.user_id == current_user.id,
        UserServiceAccount.service == s_enum.value,
    )
    res = await db.exec(stmt)
    acc = res.first()
    if acc:
        await db.delete(acc)
        await db.commit()

    code = SERVICE_CODE_MAP.get(s_enum, s_enum.value.upper()[:2])
    name = SERVICE_NAME_MAP.get(s_enum, s_enum.value.capitalize())

    return ServiceConnectionStatus(
        service=s_enum.value,
        code=code,
        name=name,
        connected=False,
        is_active=False,
        account_name=None,
        account_id=None,
    )


@router.put("/{service}/toggle", response_model=ServiceConnectionStatus)
async def toggle_service(
    service: str,
    req: ToggleServiceRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> ServiceConnectionStatus:
    """Enable or disable a service source for search and recommendations."""
    s_enum = CODE_TO_SERVICE_MAP.get(service.lower())
    if not s_enum:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown service: '{service}'",
        )

    stmt = select(UserServiceAccount).where(
        UserServiceAccount.user_id == current_user.id,
        UserServiceAccount.service == s_enum.value,
    )
    res = await db.exec(stmt)
    acc = res.first()

    if not acc:
        acc = UserServiceAccount(
            user_id=current_user.id or 0,
            service=s_enum.value,
            is_active=req.is_active,
        )
        db.add(acc)
    else:
        acc.is_active = req.is_active
        db.add(acc)

    await db.commit()
    await db.refresh(acc)

    code = SERVICE_CODE_MAP.get(s_enum, s_enum.value.upper()[:2])
    name = SERVICE_NAME_MAP.get(s_enum, s_enum.value.capitalize())

    return ServiceConnectionStatus(
        service=s_enum.value,
        code=code,
        name=name,
        connected=bool(acc.token or acc.extra_data),
        is_active=acc.is_active,
        account_name=acc.account_name,
        account_id=acc.account_id,
    )


@router.post("/youtube/oauth/device-code", response_model=YouTubeDeviceCodeResponse)
async def get_youtube_device_code(
    client_id: str | None = None,
    client_secret: str | None = None,
) -> YouTubeDeviceCodeResponse:
    """Initiates Google OAuth TV/Device Code flow for YouTube Music authorization."""
    cid = client_id or settings.YOUTUBE_CLIENT_ID
    csec = client_secret or settings.YOUTUBE_CLIENT_SECRET
    if not cid or not csec:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google OAuth CLIENT_ID and CLIENT_SECRET must be configured in settings or provided in query",
        )

    try:
        creds = OAuthCredentials(client_id=cid, client_secret=csec)
        code_data = creds.get_code()
        return YouTubeDeviceCodeResponse(
            device_code=code_data["device_code"],
            user_code=code_data["user_code"],
            verification_url=code_data["verification_url"],
            expires_in=code_data["expires_in"],
            interval=code_data["interval"],
        )
    except Exception as e:
        logger.warning("Failed to obtain YouTube device code: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка получения кода авторизации YouTube: {e}",
        )


@router.post("/youtube/oauth/poll-token")
async def poll_youtube_token(
    req: YouTubePollTokenRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """Polls Google for tokens after user enters code on verification_url and saves to user account."""
    cid = req.client_id or settings.YOUTUBE_CLIENT_ID
    csec = req.client_secret or settings.YOUTUBE_CLIENT_SECRET
    if not cid or not csec:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CLIENT_ID and CLIENT_SECRET are required",
        )

    creds = OAuthCredentials(client_id=cid, client_secret=csec)
    try:
        token_data = creds.token_from_code(req.device_code)
    except Exception as e:
        msg = str(e)
        if "authorization_pending" in msg:
            return {"status": "pending", "message": "Ожидание подтверждения пользователем"}
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ошибка авторизации: {e}",
        )

    # Save to user service accounts
    token_json = json.dumps(token_data)
    stmt = select(UserServiceAccount).where(
        UserServiceAccount.user_id == current_user.id,
        UserServiceAccount.service == Service.YOUTUBE.value,
    )
    res = await db.exec(stmt)
    acc = res.first()

    if not acc:
        acc = UserServiceAccount(
            user_id=current_user.id or 0,
            service=Service.YOUTUBE.value,
            token=token_json,
            refresh_token=token_data.get("refresh_token"),
            account_name="YouTube Music",
            is_active=True,
        )
        db.add(acc)
    else:
        acc.token = token_json
        acc.refresh_token = token_data.get("refresh_token") or acc.refresh_token
        acc.account_name = "YouTube Music"
        acc.is_active = True
        db.add(acc)

    await db.commit()
    return {"status": "connected", "service": "youtube", "account_name": "YouTube Music"}
