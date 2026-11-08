from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.deps import get_current_active_user
from app.database import get_db
from app.models.favorite import FavoriteAlbum, FavoriteTrack
from app.models.user import User
from app.schemas.favorite import (
    FavoriteAlbumCreate,
    FavoriteAlbumRead,
    FavoriteTrackCreate,
)
from app.schemas.music import AlbumRead, PlaybackInfo, TrackRead
from services.music.dto import CODE_TO_SERVICE_MAP, SERVICE_CODE_MAP, Service

router = APIRouter(prefix="/api/favorites", tags=["favorites"])


@router.get("/tracks", response_model=list[TrackRead])
async def list_favorite_tracks(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> list[TrackRead]:
    assert current_user.id is not None
    stmt = (
        select(FavoriteTrack)
        .where(FavoriteTrack.user_id == current_user.id)
        .order_by(FavoriteTrack.created_at.desc())
    )
    res = await db.exec(stmt)
    favs = res.all()

    tracks_out = []
    for f in favs:
        try:
            sources_list = json.loads(f.sources) if f.sources else []
        except Exception:
            sources_list = []

        s_code = SERVICE_CODE_MAP.get(Service(f.service), f.service[:2].upper())
        if not sources_list:
            sources_list = [s_code]

        playback = None
        if f.playback_kind and f.playback_ref:
            playback = PlaybackInfo(kind=f.playback_kind, ref=f.playback_ref)

        tracks_out.append(
            TrackRead(
                id=f.id or 1,
                track_key=f"{f.service}:{f.service_id}",
                service=f.service,
                service_id=f.service_id,
                title=f.title,
                artist=f.artist,
                cover=f.cover_url or "",
                duration=f.duration,
                sources=sources_list,
                source=s_code,
                edited=f.is_edited,
                liked=True,
                playback=playback,
            )
        )
    return tracks_out


@router.post("/tracks", response_model=TrackRead, status_code=status.HTTP_201_CREATED)
async def add_favorite_track(
    payload: FavoriteTrackCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> TrackRead:
    assert current_user.id is not None
    srv = payload.service.lower()
    # Normalize service
    resolved = CODE_TO_SERVICE_MAP.get(srv, CODE_TO_SERVICE_MAP.get(srv.upper()))
    srv_str = resolved.value if resolved else srv

    # Check if already in favorites
    stmt = select(FavoriteTrack).where(
        FavoriteTrack.user_id == current_user.id,
        FavoriteTrack.service == srv_str,
        FavoriteTrack.service_id == payload.service_id,
    )
    res = await db.exec(stmt)
    existing = res.first()
    if existing:
        return TrackRead(
            id=existing.id or 1,
            track_key=f"{existing.service}:{existing.service_id}",
            service=existing.service,
            service_id=existing.service_id,
            title=existing.title,
            artist=existing.artist,
            cover=existing.cover_url or "",
            duration=existing.duration,
            sources=json.loads(existing.sources) if existing.sources else [SERVICE_CODE_MAP.get(Service(existing.service), "TRK")],
            source=SERVICE_CODE_MAP.get(Service(existing.service), "TRK"),
            edited=existing.is_edited,
            liked=True,
            playback=PlaybackInfo(kind=existing.playback_kind, ref=existing.playback_ref) if existing.playback_kind and existing.playback_ref else None,
        )

    sources_str = json.dumps(payload.sources) if payload.sources else "[]"
    new_fav = FavoriteTrack(
        user_id=current_user.id,
        service=srv_str,
        service_id=payload.service_id,
        title=payload.title,
        artist=payload.artist,
        album=payload.album,
        cover_url=payload.cover_url,
        duration=payload.duration,
        sources=sources_str,
        playback_kind=payload.playback_kind,
        playback_ref=payload.playback_ref,
        is_edited=payload.is_edited,
    )
    db.add(new_fav)
    await db.commit()
    await db.refresh(new_fav)

    s_code = SERVICE_CODE_MAP.get(Service(srv_str), srv_str[:2].upper())
    src_list = payload.sources or [s_code]

    assert new_fav.id is not None
    return TrackRead(
        id=new_fav.id,
        track_key=f"{new_fav.service}:{new_fav.service_id}",
        service=new_fav.service,
        service_id=new_fav.service_id,
        title=new_fav.title,
        artist=new_fav.artist,
        cover=new_fav.cover_url or "",
        duration=new_fav.duration,
        sources=src_list,
        source=s_code,
        edited=new_fav.is_edited,
        liked=True,
        playback=PlaybackInfo(kind=new_fav.playback_kind, ref=new_fav.playback_ref) if new_fav.playback_kind and new_fav.playback_ref else None,
    )


@router.delete("/tracks/{service}/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_favorite_track(
    service: str,
    service_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> None:
    assert current_user.id is not None
    srv = service.lower()
    resolved = CODE_TO_SERVICE_MAP.get(srv, CODE_TO_SERVICE_MAP.get(srv.upper()))
    srv_str = resolved.value if resolved else srv

    stmt = select(FavoriteTrack).where(
        FavoriteTrack.user_id == current_user.id,
        FavoriteTrack.service == srv_str,
        FavoriteTrack.service_id == service_id,
    )
    res = await db.exec(stmt)
    fav = res.first()
    if not fav:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Track not in favorites")

    await db.delete(fav)
    await db.commit()


@router.get("/check")
async def check_favorites(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> dict[str, list[str]]:
    assert current_user.id is not None
    stmt = select(FavoriteTrack.service, FavoriteTrack.service_id).where(
        FavoriteTrack.user_id == current_user.id
    )
    res = await db.exec(stmt)
    keys = [f"{srv}:{s_id}" for srv, s_id in res.all()]
    return {"liked_keys": keys}


@router.get("/albums", response_model=list[AlbumRead])
async def list_favorite_albums(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> list[AlbumRead]:
    assert current_user.id is not None
    stmt = select(FavoriteAlbum).where(FavoriteAlbum.user_id == current_user.id).order_by(FavoriteAlbum.created_at.desc())
    res = await db.exec(stmt)
    albums = res.all()

    return [
        AlbumRead(
            id=a.id or 1,
            service=a.service,
            service_id=a.service_id,
            title=a.title,
            subtitle=a.subtitle or "Альбом",
            cover=a.cover_url or "",
        )
        for a in albums
    ]


@router.post("/albums", response_model=AlbumRead, status_code=status.HTTP_201_CREATED)
async def add_favorite_album(
    payload: FavoriteAlbumCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> AlbumRead:
    assert current_user.id is not None
    srv = payload.service.lower()
    resolved = CODE_TO_SERVICE_MAP.get(srv, CODE_TO_SERVICE_MAP.get(srv.upper()))
    srv_str = resolved.value if resolved else srv

    stmt = select(FavoriteAlbum).where(
        FavoriteAlbum.user_id == current_user.id,
        FavoriteAlbum.service == srv_str,
        FavoriteAlbum.service_id == payload.service_id,
    )
    res = await db.exec(stmt)
    existing = res.first()
    if existing:
        return AlbumRead(
            id=existing.id or 1,
            service=existing.service,
            service_id=existing.service_id,
            title=existing.title,
            subtitle=existing.subtitle or "Альбом",
            cover=existing.cover_url or "",
        )

    new_fav = FavoriteAlbum(
        user_id=current_user.id,
        service=srv_str,
        service_id=payload.service_id,
        title=payload.title,
        subtitle=payload.subtitle,
        cover_url=payload.cover_url,
    )
    db.add(new_fav)
    await db.commit()
    await db.refresh(new_fav)

    assert new_fav.id is not None
    return AlbumRead(
        id=new_fav.id,
        service=new_fav.service,
        service_id=new_fav.service_id,
        title=new_fav.title,
        subtitle=new_fav.subtitle or "Альбом",
        cover=new_fav.cover_url or "",
    )


@router.delete("/albums/{service}/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_favorite_album(
    service: str,
    service_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> None:
    assert current_user.id is not None
    srv = service.lower()
    resolved = CODE_TO_SERVICE_MAP.get(srv, CODE_TO_SERVICE_MAP.get(srv.upper()))
    srv_str = resolved.value if resolved else srv

    stmt = select(FavoriteAlbum).where(
        FavoriteAlbum.user_id == current_user.id,
        FavoriteAlbum.service == srv_str,
        FavoriteAlbum.service_id == service_id,
    )
    res = await db.exec(stmt)
    fav = res.first()
    if not fav:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Album not in favorites")

    await db.delete(fav)
    await db.commit()
