from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.deps import get_optional_current_user
from app.database import get_db
from app.models.favorite import FavoriteTrack
from app.models.preference import UserServicePreference
from app.models.upload import UserUpload
from app.models.user import User
from app.schemas.music import (
    AlbumRead,
    ArtistRead,
    MusicSearchResponse,
    PlaybackInfo,
    PlaylistSearchResult,
    TrackRead,
)
from services.music.aggregator import aggregator
from services.music.dto import (
    CODE_TO_SERVICE_MAP,
    SERVICE_CODE_MAP,
    AlbumDTO,
    ArtistDTO,
    PlaylistDTO,
    SearchType,
    Service,
    TrackDTO,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/music", tags=["music"])


@router.get("/search", response_model=MusicSearchResponse)
async def search_music(
    q: str = Query(..., min_length=1, description="Search query string"),
    services: str | None = Query(None, description="Comma-separated services: yandex,spotify,soundcloud,youtube,local"),
    types: str | None = Query("track,album", description="Comma-separated types: track,album,artist,playlist"),
    limit: int = Query(10, ge=1, le=50, description="Results limit per service"),
    current_user: Annotated[User | None, Depends(get_optional_current_user)] = None,
    db: AsyncSession = Depends(get_db),
) -> MusicSearchResponse:
    # 1. Resolve enabled services
    target_services: list[str] = []
    if services:
        target_services = [s.strip() for s in services.split(",") if s.strip()]
    elif current_user and current_user.id:
        stmt = select(UserServicePreference).where(
            UserServicePreference.user_id == current_user.id,
            UserServicePreference.is_enabled == True,  # noqa: E712
        )
        res = await db.exec(stmt)
        user_prefs = res.all()
        if user_prefs:
            target_services = [p.service for p in user_prefs]

    # Parse search types
    search_types = set()
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

    # 2. Query external services via aggregator
    agg_result = await aggregator.search(
        query=q,
        services=target_services or None,
        types=frozenset(search_types),
        limit_per_service=limit,
    )

    # 3. Search user's uploaded tracks if local search is requested or by default
    local_tracks: list[TrackDTO] = []
    if current_user and current_user.id:
        upload_stmt = select(UserUpload).where(
            UserUpload.user_id == current_user.id,
            UserUpload.title.ilike(f"%{q}%") | UserUpload.artist.ilike(f"%{q}%"),
        ).limit(limit)
        upload_res = await db.exec(upload_stmt)
        uploads = upload_res.all()

        for u in uploads:
            local_tracks.append(
                TrackDTO(
                    service=Service.LOCAL,
                    service_id=str(u.id),
                    title=u.title,
                    artists=(u.artist or "Моя музыка",),
                    duration_ms=u.duration_seconds * 1000,
                    playback=None,
                    direct_audio_url=f"/api/uploads/{u.id}/stream",
                    artwork_url=u.cover_url,
                    sources=("ФАЙЛ",),
                    edited=u.is_edited,
                )
            )

    combined_tracks = list(local_tracks) + list(agg_result.tracks)

    # 4. Check user favorites to populate liked flag
    liked_keys: set[str] = set()
    if current_user and current_user.id:
        fav_stmt = select(FavoriteTrack).where(FavoriteTrack.user_id == current_user.id)
        fav_res = await db.exec(fav_stmt)
        for fav in fav_res.all():
            liked_keys.add(f"{fav.service}:{fav.service_id}")

    # 5. Format to frontend TrackRead
    tracks_out: list[TrackRead] = []
    for t in combined_tracks:
        t_dict = t.to_frontend_dict()
        t_key = f"{t.service.value}:{t.service_id}"
        t_dict["liked"] = t_key in liked_keys
        tracks_out.append(TrackRead(**t_dict))

    albums_out = [AlbumRead(**alb.to_frontend_dict()) for alb in agg_result.albums]

    artists_out = [
        ArtistRead(
            service=a.service.value,
            service_id=a.service_id,
            name=a.name,
            genres=list(a.genres),
            cover=str(a.artwork_url) if a.artwork_url else None,
            external_url=str(a.external_url) if a.external_url else None,
        )
        for a in agg_result.artists
    ]

    playlists_out = [
        PlaylistSearchResult(
            id=abs(hash(f"{p.service.value}:{p.service_id}")) % 10_000_000 + 1,
            service=p.service.value,
            service_id=p.service_id,
            name=p.title,
            cover=str(p.artwork_url) if p.artwork_url else "",
            description=p.description,
            tracks_count=p.tracks_count or (len(p.tracks) if p.tracks else 0),
        )
        for p in agg_result.playlists
    ]

    errors_out = [err.model_dump() for err in agg_result.errors]

    return MusicSearchResponse(
        query=q,
        tracks=tracks_out,
        albums=albums_out,
        artists=artists_out,
        playlists=playlists_out,
        errors=errors_out,
    )


@router.get("/tracks/{service}/{service_id}", response_model=TrackRead)
async def get_track(
    service: str,
    service_id: str,
    current_user: Annotated[User | None, Depends(get_optional_current_user)] = None,
    db: AsyncSession = Depends(get_db),
) -> TrackRead:
    # Check local tracks
    if service.lower() in ("local", "loc", "файл") and current_user and current_user.id:
        try:
            up_id = int(service_id)
            stmt = select(UserUpload).where(UserUpload.id == up_id, UserUpload.user_id == current_user.id)
            res = await db.exec(stmt)
            upload = res.first()
            if upload:
                return TrackRead(
                    id=upload.id or 1,
                    track_key=f"local:{upload.id}",
                    service="local",
                    service_id=str(upload.id),
                    title=upload.title,
                    artist=upload.artist,
                    cover=upload.cover_url or "",
                    duration=upload.duration_seconds,
                    sources=["ФАЙЛ"],
                    source="ФАЙЛ",
                    edited=upload.is_edited,
                    liked=False,
                    direct_audio_url=f"/api/uploads/{upload.id}/stream",
                )
        except ValueError:
            pass

    track_dto = await aggregator.get_track(service, service_id)
    if not track_dto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Track {service_id} on {service} not found",
        )

    t_dict = track_dto.to_frontend_dict()
    if current_user and current_user.id:
        fav_stmt = select(FavoriteTrack).where(
            FavoriteTrack.user_id == current_user.id,
            FavoriteTrack.service == track_dto.service.value,
            FavoriteTrack.service_id == track_dto.service_id,
        )
        fav_res = await db.exec(fav_stmt)
        t_dict["liked"] = fav_res.first() is not None

    return TrackRead(**t_dict)


@router.get("/playback/{service}/{service_id}", response_model=PlaybackInfo)
async def get_playback(
    service: str,
    service_id: str,
    current_user: Annotated[User | None, Depends(get_optional_current_user)] = None,
) -> PlaybackInfo:
    if service.lower() in ("local", "loc", "файл"):
        return PlaybackInfo(
            kind="audio_stream",
            ref=f"/api/uploads/{service_id}/stream",
        )

    track_dto = await aggregator.get_track(service, service_id)
    if not track_dto or not track_dto.playback:
        # Fallback ref based on service
        s_enum = CODE_TO_SERVICE_MAP.get(service.lower())
        if s_enum == Service.YOUTUBE:
            return PlaybackInfo(kind="youtube_iframe", ref=service_id)
        elif s_enum == Service.SOUNDCLOUD:
            return PlaybackInfo(kind="soundcloud_widget", ref=f"https://soundcloud.com/track/{service_id}")
        elif s_enum == Service.SPOTIFY:
            return PlaybackInfo(kind="spotify_sdk", ref=f"spotify:track:{service_id}")
        elif s_enum == Service.YANDEX:
            return PlaybackInfo(kind="yandex_iframe", ref=service_id)

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Playback info not available for track {service_id} on {service}",
        )

    return PlaybackInfo(kind=track_dto.playback.kind.value, ref=track_dto.playback.ref)


@router.get("/albums/{service}/{service_id}", response_model=AlbumRead)
async def get_album(service: str, service_id: str) -> AlbumRead:
    alb_dto = await aggregator.get_album(service, service_id)
    if not alb_dto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Album {service_id} on {service} not found",
        )
    return AlbumRead(**alb_dto.to_frontend_dict())


@router.get("/artists/{service}/{service_id}", response_model=ArtistRead)
async def get_artist(service: str, service_id: str) -> ArtistRead:
    art_dto = await aggregator.get_artist(service, service_id)
    if not art_dto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artist {service_id} on {service} not found",
        )
    return ArtistRead(
        service=art_dto.service.value,
        service_id=art_dto.service_id,
        name=art_dto.name,
        genres=list(art_dto.genres),
        cover=str(art_dto.artwork_url) if art_dto.artwork_url else None,
        external_url=str(art_dto.external_url) if art_dto.external_url else None,
    )
