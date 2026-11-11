from __future__ import annotations

import json
import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from starlette.concurrency import run_in_threadpool
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
    VkLoginRequest,
    YandexPollTokenRequest,
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


@router.post("/yandex/oauth/device-code", response_model=YouTubeDeviceCodeResponse)
async def get_yandex_device_code(
    current_user: Annotated[User, Depends(get_current_user)],
) -> YouTubeDeviceCodeResponse:
    """Starts Yandex OAuth Device Flow: returns a code the user enters on the verification page."""
    from yandex_music import Client

    try:
        code = await run_in_threadpool(Client().request_device_code)
    except Exception as e:
        logger.warning("Failed to obtain Yandex device code: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Не удалось получить код входа Яндекса: {e}",
        )

    return YouTubeDeviceCodeResponse(
        device_code=code.device_code,
        user_code=code.user_code,
        verification_url=code.verification_url,
        expires_in=code.expires_in,
        interval=code.interval,
    )


@router.post("/yandex/oauth/poll-token")
async def poll_yandex_token(
    req: YandexPollTokenRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """Polls Yandex for the token after the user confirms the code, then saves it to the user account."""
    from yandex_music import Client
    from yandex_music.exceptions import DeviceAuthError

    try:
        token = await run_in_threadpool(Client().poll_device_token, req.device_code)
    except DeviceAuthError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Вход в Яндекс не завершён: {e}",
        )

    if token is None:
        return {"status": "pending", "message": "Ожидание подтверждения пользователем"}

    account_name = "Яндекс Музыка"
    account_id: str | None = None
    try:
        ym_client = await run_in_threadpool(Client(token.access_token).init)
        if ym_client.me and ym_client.me.account:
            account_name = ym_client.me.account.full_name or ym_client.me.account.login or account_name
            account_id = str(ym_client.me.account.uid) if ym_client.me.account.uid else None
    except Exception as e:
        logger.warning("Yandex account info failed: %s", e)

    stmt = select(UserServiceAccount).where(
        UserServiceAccount.user_id == current_user.id,
        UserServiceAccount.service == Service.YANDEX.value,
    )
    res = await db.exec(stmt)
    acc = res.first()

    if not acc:
        acc = UserServiceAccount(
            user_id=current_user.id or 0,
            service=Service.YANDEX.value,
            token=token.access_token,
            refresh_token=token.refresh_token,
            account_name=account_name,
            account_id=account_id,
            is_active=True,
        )
        db.add(acc)
    else:
        acc.token = token.access_token
        acc.refresh_token = token.refresh_token or acc.refresh_token
        acc.account_name = account_name
        acc.account_id = account_id or acc.account_id
        acc.is_active = True
        db.add(acc)

    await db.commit()
    return {"status": "connected", "service": "yandex", "account_name": account_name}


def _vk_login_step(login: str, password: str, code: str | None) -> dict[str, Any]:
    """One step of VK login by login/password. Returns the token or what VK asks for next."""
    from vkpymusic import Service as VkService
    from vkpymusic import VkMobileClient
    from vkpymusic.vk_api import VkApiException
    from vkpymusic.vk_api.vk_api_extensions import make_request
    from vkpymusic.vk_api.vk_api_request_builder import VkApiRequestBuilder

    client = VkMobileClient
    request = VkApiRequestBuilder.build_req_auth(login=login, password=password, client=client, code=code)
    try:
        response = make_request(request)
    except VkApiException as e:
        details = e.details if isinstance(e.details, dict) else {}
        error = details.get("error")
        if error == "need_validation":
            sid = details.get("validation_sid")
            if sid and not code:
                try:
                    make_request(VkApiRequestBuilder.build_req_2fa_code(client=client, sid=sid))
                except VkApiException:
                    pass
            return {
                "status": "need_code",
                "validation_type": details.get("validation_type"),
                "phone_mask": details.get("phone_mask"),
            }
        if error == "invalid_request":
            return {"status": "need_code", "invalid_code": True}
        if error == "need_captcha":
            return {"status": "need_captcha"}
        if error == "invalid_client":
            return {"status": "error", "message": "Неверный логин или пароль"}
        if error == "9;Flood control" or details.get("error_type") == "password_bruteforce_attempt":
            return {"status": "error", "message": "Слишком много попыток входа. Попробуйте позже"}
        return {"status": "error", "message": details.get("error_description") or "VK отклонил вход"}

    token = response.data.get("access_token") if response and response.data else None
    if not token:
        return {"status": "error", "message": "VK не выдал токен"}

    account_name = "VK Музыка"
    try:
        info = VkService(client.user_agent, token).get_user_info()
        name = " ".join(part for part in (getattr(info, "first_name", None), getattr(info, "last_name", None)) if part)
        account_name = name or account_name
    except Exception as e:
        logger.warning("VK user info failed: %s", type(e).__name__)

    return {
        "status": "connected",
        "token": token,
        "user_agent": client.user_agent,
        "account_name": account_name,
        "account_id": str(response.data.get("user_id")) if response.data.get("user_id") else None,
    }


@router.post("/vk/login")
async def login_vk(
    req: VkLoginRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """Links VK Music by login and password. The password is used once and never stored."""
    if not req.login.strip() or not req.password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Введите логин и пароль VK")

    try:
        result = await run_in_threadpool(
            _vk_login_step, req.login.strip(), req.password, (req.code or "").strip() or None
        )
    except Exception as e:
        logger.warning("VK login failed: %s", type(e).__name__)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Не удалось связаться с VK")

    if result["status"] == "error":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["message"])
    if result["status"] != "connected":
        return result

    stmt = select(UserServiceAccount).where(
        UserServiceAccount.user_id == current_user.id,
        UserServiceAccount.service == Service.VK.value,
    )
    res = await db.exec(stmt)
    acc = res.first()
    extra_data = json.dumps({"user_agent": result["user_agent"]})

    if not acc:
        acc = UserServiceAccount(
            user_id=current_user.id or 0,
            service=Service.VK.value,
            token=result["token"],
            extra_data=extra_data,
            account_name=result["account_name"],
            account_id=result["account_id"],
            is_active=True,
        )
        db.add(acc)
    else:
        acc.token = result["token"]
        acc.extra_data = extra_data
        acc.account_name = result["account_name"]
        acc.account_id = result["account_id"] or acc.account_id
        acc.is_active = True
        db.add(acc)

    await db.commit()
    return {"status": "connected", "service": "vk", "account_name": result["account_name"]}
