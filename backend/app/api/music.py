from __future__ import annotations

import logging
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse, StreamingResponse
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.deps import get_current_user, get_optional_current_user
from app.config import settings
from app.core.streaming import (
    create_service_stream_signature,
    create_stream_signature,
    verify_service_stream_signature,
)
from app.database import get_db
from app.models.service_account import UserServiceAccount
from app.models.upload import UserUpload
from app.models.user import User
from app.schemas.music import (
    AlbumRead,
    ArtistRead,
    MusicSearchResponse,
    PlaybackInfo,
    PlaylistRead,
    ServiceErrorRead,
    TrackRead,
)
from app.schemas.service import ServiceStatusRead
from services.music.aggregator import aggregator
from services.music.base import BaseMusicAdapter
from services.music.dto import CODE_TO_SERVICE_MAP, SearchType, Service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/music", tags=["music"])


async def get_user_adapter(
    db: AsyncSession,
    user: User | None,
    service: str,
) -> BaseMusicAdapter | None:
    """Adapter with the user's own credentials (full tracks instead of previews), if the service is linked."""
    s_enum = CODE_TO_SERVICE_MAP.get(service.lower())
    if not user or not user.id or not s_enum:
        return None
    stmt = select(UserServiceAccount).where(
        UserServiceAccount.user_id == user.id,
        UserServiceAccount.service == s_enum.value,
    )
    res = await db.exec(stmt)
    acc = res.first()
    if not acc or not acc.is_active or not (acc.token or acc.extra_data):
        return None
    return aggregator.create_user_adapter(s_enum, token=acc.token, extra_data=acc.extra_data)


@router.get("/services", response_model=list[ServiceStatusRead])
async def list_music_services() -> list[ServiceStatusRead]:
    """Returns the list of music source services and their online status."""
    statuses = aggregator.get_services_status()
    return [ServiceStatusRead(**s) for s in statuses]


@router.get("/search", response_model=MusicSearchResponse)
async def search_music(
    q: str = Query(..., min_length=1, description="Search query string"),
    services: str | None = Query(None, description="Comma-separated services: yandex,youtube,vk,spotify,soundcloud"),
    types: str | None = Query("track,album", description="Comma-separated types: track,album,artist,playlist"),
    limit: int = Query(
        settings.DEFAULT_SEARCH_LIMIT,
        ge=1,
        le=settings.MAX_SEARCH_LIMIT,
        description="Results limit per service",
    ),
    current_user: Annotated[User | None, Depends(get_optional_current_user)] = None,
    db: AsyncSession = Depends(get_db),
) -> MusicSearchResponse:
    """Search for tracks, albums, artists, and playlists across enabled music services."""
    target_services: list[str] = []
    user_adapters: dict[Service, BaseMusicAdapter] = {}

    if current_user and current_user.id:
        stmt = select(UserServiceAccount).where(UserServiceAccount.user_id == current_user.id)
        res = await db.exec(stmt)
        user_accounts = {acc.service.lower(): acc for acc in res.all()}

        # Build custom user adapters
        for srv_name, acc in user_accounts.items():
            s_enum = CODE_TO_SERVICE_MAP.get(srv_name)
            if s_enum and acc.is_active:
                adapter = aggregator.create_user_adapter(s_enum, token=acc.token, extra_data=acc.extra_data)
                if adapter:
                    user_adapters[s_enum] = adapter

        if not services and user_accounts:
            # Filter default services to those active in user settings
            target_services = [acc.service for acc in user_accounts.values() if acc.is_active]

    if services:
        target_services = [s.strip() for s in services.split(",") if s.strip()]

    # Parse search types
    search_types: set[SearchType] = set()
    if types:
        for t in types.split(","):
            t_clean = t.strip().lower()
            if t_clean in ("track", "tracks"):
                search_types.add(SearchType.TRACK)
            elif t_clean in ("album", "albums"):
                search_types.add(SearchType.ALBUM)
            elif t_clean in ("artist", "artists"):
                search_types.add(SearchType.ARTIST)
            elif t_clean in ("playlist", "playlists"):
                search_types.add(SearchType.PLAYLIST)
    if not search_types:
        search_types = {SearchType.TRACK}

    # Query music services via aggregator
    agg_result = await aggregator.search(
        query=q,
        services=target_services or None,
        types=frozenset(search_types),
        limit_per_service=limit,
        user_adapters=user_adapters or None,
    )

    tracks_out = [TrackRead(**t.to_frontend_dict()) for t in agg_result.tracks]
    albums_out = [AlbumRead(**alb.to_frontend_dict()) for alb in agg_result.albums]
    artists_out = [
        ArtistRead(
            service=a.service.value,
            service_id=a.service_id,
            name=a.name,
            genres=list(a.genres),
            cover=str(a.artwork_url) if a.artwork_url else None,
            artwork_url=str(a.artwork_url) if a.artwork_url else None,
            external_url=str(a.external_url) if a.external_url else None,
        )
        for a in agg_result.artists
    ]
    playlists_out = [PlaylistRead(**p.to_frontend_dict()) for p in agg_result.playlists]
    errors_out = [
        ServiceErrorRead(
            service=err.service.value,
            kind=err.kind.value,
            message=err.message,
            status_code=err.status_code,
        )
        for err in agg_result.errors
    ]

    return MusicSearchResponse(
        query=q,
        tracks=tracks_out,
        albums=albums_out,
        artists=artists_out,
        playlists=playlists_out,
        errors=errors_out,
    )


@router.get("/me/playlists", response_model=list[PlaylistRead])
async def get_my_playlists(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> list[PlaylistRead]:
    """Retrieve user's library playlists from all connected external services."""
    stmt = select(UserServiceAccount).where(
        UserServiceAccount.user_id == current_user.id,
        UserServiceAccount.is_active == True,  # noqa: E712
    )
    res = await db.exec(stmt)
    accounts = res.all()

    all_playlists: list[PlaylistRead] = []
    for acc in accounts:
        pls = await aggregator.get_user_playlists(
            service=acc.service,
            token=acc.token,
            extra_data=acc.extra_data,
            account_id=acc.account_id,
        )
        for p in pls:
            all_playlists.append(PlaylistRead(**p.to_frontend_dict()))

    return all_playlists


@router.get("/me/favorites", response_model=list[TrackRead])
async def get_my_favorites(
    current_user: Annotated[User, Depends(get_current_user)],
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[TrackRead]:
    """Retrieve user's favorite / liked tracks from all connected external services."""
    stmt = select(UserServiceAccount).where(
        UserServiceAccount.user_id == current_user.id,
        UserServiceAccount.is_active == True,  # noqa: E712
    )
    res = await db.exec(stmt)
    accounts = res.all()

    all_tracks: list[TrackRead] = []
    for acc in accounts:
        tracks = await aggregator.get_user_favorites(
            service=acc.service,
            token=acc.token,
            extra_data=acc.extra_data,
            account_id=acc.account_id,
            limit=limit,
        )
        for t in tracks:
            t_dict = t.to_frontend_dict()
            t_dict["liked"] = True
            all_tracks.append(TrackRead(**t_dict))

    return all_tracks


@router.get("/tracks/{service}/{service_id}", response_model=TrackRead)
async def get_track(
    service: str,
    service_id: str,
    current_user: Annotated[User | None, Depends(get_optional_current_user)] = None,
    db: AsyncSession = Depends(get_db),
) -> TrackRead:
    """Retrieve full track metadata and playback parameters by service and service ID."""
    if service.lower() == "local":
        try:
            up_id = int(service_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Local track '{service_id}' not found",
            )
        upload = await db.get(UserUpload, up_id)
        if not upload:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Local track '{service_id}' not found",
            )
        sig = create_stream_signature(upload.id or 0, upload.user_id)
        stream_url = f"/api/uploads/{upload.id}/stream?sig={sig}"
        cover_val = upload.cover_template if upload.cover_template else (
            f"/api/uploads/{upload.id}/cover" if upload.cover_file else None
        )
        return TrackRead(
            id=upload.id or 0,
            track_key=f"local:{upload.id}",
            service="local",
            service_id=str(upload.id),
            title=upload.title,
            artist=upload.artist,
            artists=[upload.artist],
            cover=cover_val or "",
            artwork_url=cover_val,
            duration=upload.duration_seconds,
            duration_ms=upload.duration_seconds * 1000,
            sources=["ФАЙЛ"],
            source="ФАЙЛ",
            is_playable=True,
            liked=False,
            direct_audio_url=stream_url,
            stream_url=stream_url,
            playback=PlaybackInfo(
                kind="direct_url",
                ref=stream_url,
                direct_audio_url=stream_url,
            ),
        )

    user_adapter = await get_user_adapter(db, current_user, service)
    track_dto = await aggregator.get_track(service, service_id, adapter=user_adapter)
    if not track_dto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Track '{service_id}' on service '{service}' not found",
        )

    t_dict = track_dto.to_frontend_dict()
    if track_dto.direct_audio_url and track_dto.service == Service.YANDEX:
        # Yandex CDN blocks browser origins (CORS 403 Forbidden). Route through stream proxy.
        stream_url = f"/api/music/tracks/{track_dto.service.value}/{track_dto.service_id}/stream"
        if current_user and current_user.id:
            sig = create_service_stream_signature(track_dto.service.value, track_dto.service_id, current_user.id)
            stream_url = f"{stream_url}?u={current_user.id}&sig={sig}"
        t_dict["direct_audio_url"] = stream_url
        if t_dict.get("playback"):
            t_dict["playback"]["direct_audio_url"] = stream_url
        t_dict["stream_url"] = stream_url

    return TrackRead(**t_dict)


@router.get("/playback/{service}/{service_id}", response_model=PlaybackInfo)
async def get_playback_info(
    service: str,
    service_id: str,
    current_user: Annotated[User | None, Depends(get_optional_current_user)] = None,
    db: AsyncSession = Depends(get_db),
) -> PlaybackInfo:
    """Retrieve playback parameters (iframe ref, SDK ref, direct audio url) for a track."""
    if service.lower() == "local":
        try:
            up_id = int(service_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Local track '{service_id}' not found",
            )
        upload = await db.get(UserUpload, up_id)
        if not upload:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Local track '{service_id}' not found",
            )
        sig = create_stream_signature(upload.id or 0, upload.user_id)
        stream_url = f"/api/uploads/{upload.id}/stream?sig={sig}"
        return PlaybackInfo(
            kind="direct_url",
            ref=stream_url,
            direct_audio_url=stream_url,
        )

    user_adapter = await get_user_adapter(db, current_user, service)
    track_dto = await aggregator.get_track(service, service_id, adapter=user_adapter)
    if not track_dto:
        # Fallback ref based on known service format if track metadata cannot be resolved
        s_enum = CODE_TO_SERVICE_MAP.get(service.lower())
        if s_enum == Service.YOUTUBE:
            return PlaybackInfo(kind="youtube_iframe", ref=service_id)
        elif s_enum == Service.SOUNDCLOUD:
            return PlaybackInfo(kind="soundcloud_widget", ref=f"https://soundcloud.com/track/{service_id}")
        elif s_enum == Service.SPOTIFY:
            return PlaybackInfo(kind="spotify_sdk", ref=f"spotify:track:{service_id}")
        elif s_enum == Service.YANDEX:
            return PlaybackInfo(kind="yandex_iframe", ref=service_id)
        elif s_enum == Service.VK:
            return PlaybackInfo(kind="direct_url", ref=service_id)

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Track '{service_id}' on service '{service}' not found",
        )

    if track_dto.playback:
        return PlaybackInfo(
            kind=track_dto.playback.kind.value,
            ref=track_dto.playback.ref,
            direct_audio_url=str(track_dto.direct_audio_url) if track_dto.direct_audio_url else None,
        )

    if track_dto.direct_audio_url:
        return PlaybackInfo(
            kind="direct_url",
            ref=str(track_dto.direct_audio_url),
            direct_audio_url=str(track_dto.direct_audio_url),
        )

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Playback information not available for track '{service_id}' on service '{service}'",
    )


@router.get("/tracks/{service}/{service_id}/stream")
async def stream_track_audio(
    service: str,
    service_id: str,
    request: Request,
    redirect: bool = Query(False, description="Redirect directly to CDN audio URL"),
    u: int | None = Query(None, description="User ID for signed stream"),
    sig: str | None = Query(None, description="HMAC stream signature"),
    current_user: Annotated[User | None, Depends(get_optional_current_user)] = None,
    db: AsyncSession = Depends(get_db),
):
    """Stream audio content for a track with HTTP Range header support or redirect to direct audio URL."""
    if service.lower() == "local":
        return RedirectResponse(
            url=f"/api/uploads/{service_id}/stream",
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        )

    # Authenticate user from Authorization header OR verified time-limited HMAC stream signature
    effective_user: User | None = current_user
    if not effective_user and u is not None and sig:
        if verify_service_stream_signature(service, service_id, u, sig):
            effective_user = await db.get(User, u)

    user_adapter = await get_user_adapter(db, effective_user, service)
    track_dto = await aggregator.get_track(service, service_id, adapter=user_adapter)
    if not track_dto or not track_dto.direct_audio_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audio stream not available for track '{service_id}' on service '{service}'",
        )

    audio_url = str(track_dto.direct_audio_url)

    if redirect:
        return RedirectResponse(url=audio_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    range_header = request.headers.get("range")
    if range_header:
        headers["Range"] = range_header

    client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
    req = client.build_request("GET", audio_url, headers=headers)
    r = await client.send(req, stream=True)

    if r.status_code >= 400:
        await r.aclose()
        await client.aclose()
        raise HTTPException(
            status_code=r.status_code,
            detail="Failed to stream audio from provider CDN",
        )

    async def aiter_stream():
        try:
            async for chunk in r.aiter_bytes():
                yield chunk
        finally:
            await r.aclose()
            await client.aclose()

    resp_headers = {
        "Accept-Ranges": "bytes",
        "Content-Disposition": f'inline; filename="{track_dto.service_id}.mp3"',
    }
    for h in ("content-range", "content-length", "content-type"):
        if h in r.headers:
            resp_headers[h.title()] = r.headers[h]

    return StreamingResponse(
        aiter_stream(),
        status_code=r.status_code,
        media_type=r.headers.get("content-type", "audio/mpeg"),
        headers=resp_headers,
    )


@router.get("/albums/{service}/{service_id}", response_model=AlbumRead)
async def get_album(service: str, service_id: str) -> AlbumRead:
    """Retrieve album details and tracklist by service and album ID."""
    alb_dto = await aggregator.get_album(service, service_id)
    if not alb_dto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Album '{service_id}' on service '{service}' not found",
        )
    return AlbumRead(**alb_dto.to_frontend_dict())


@router.get("/artists/{service}/{service_id}", response_model=ArtistRead)
async def get_artist(service: str, service_id: str) -> ArtistRead:
    """Retrieve artist profile and details by service and artist ID."""
    art_dto = await aggregator.get_artist(service, service_id)
    if not art_dto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artist '{service_id}' on service '{service}' not found",
        )
    return ArtistRead(
        service=art_dto.service.value,
        service_id=art_dto.service_id,
        name=art_dto.name,
        genres=list(art_dto.genres),
        cover=str(art_dto.artwork_url) if art_dto.artwork_url else None,
        artwork_url=str(art_dto.artwork_url) if art_dto.artwork_url else None,
        external_url=str(art_dto.external_url) if art_dto.external_url else None,
    )


@router.get("/playlists/{service}/{service_id}", response_model=PlaylistRead)
async def get_playlist(
    service: str,
    service_id: str,
    current_user: Annotated[User | None, Depends(get_optional_current_user)] = None,
    db: AsyncSession = Depends(get_db),
) -> PlaylistRead:
    """Retrieve playlist details and tracklist by service and playlist ID (private ones need a linked account)."""
    user_adapter = await get_user_adapter(db, current_user, service)
    pl_dto = await aggregator.get_playlist(service, service_id, adapter=user_adapter)
    if not pl_dto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Playlist '{service_id}' on service '{service}' not found",
        )
    return PlaylistRead(**pl_dto.to_frontend_dict())
