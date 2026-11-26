from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import delete, func
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.deps import get_current_active_user
from app.api.music import (
    _get_source_code,
    _get_user_liked_keys,
    _yandex_proxy_url,
    get_user_adapter,
)
from app.core.streaming import create_stream_signature
from app.database import get_db
from app.models.playlist import UserPlaylist, UserPlaylistTrack
from app.models.upload import UserUpload
from app.models.user import User
from app.schemas.music import PlaybackInfo, TrackRead
from app.schemas.playlist import (
    PlaylistCreateRequest,
    PlaylistUpdateRequest,
    TrackRef,
    UserPlaylistRead,
)
from services.music.aggregator import aggregator
from services.music.dto import Service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/playlists", tags=["playlists"])

RESERVED_PLAYLIST_NAME = "понравившиеся"


def _normalize_playlist_name(raw_name: str) -> tuple[str, str]:
    """Trim playlist name, reject empty or reserved names, and return (clean, normalized)."""
    cleaned = raw_name.strip()
    if not cleaned:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Название плейлиста не может быть пустым",
        )
    normalized = cleaned.casefold()
    if normalized == RESERVED_PLAYLIST_NAME:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Название «Понравившиеся» зарезервировано",
        )
    return cleaned, normalized


async def _ensure_unique_name(
    db: AsyncSession,
    user_id: int,
    cleaned_name: str,
    normalized_name: str,
    exclude_playlist_id: int | None = None,
) -> None:
    stmt = select(UserPlaylist).where(
        UserPlaylist.user_id == user_id,
        UserPlaylist.normalized_name == normalized_name,
    )
    if exclude_playlist_id is not None:
        stmt = stmt.where(UserPlaylist.id != exclude_playlist_id)
    res = await db.exec(stmt)
    if res.first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Плейлист «{cleaned_name}» уже существует",
        )


async def _get_owned_playlist(
    db: AsyncSession,
    user_id: int,
    playlist_id: int,
) -> UserPlaylist:
    stmt = select(UserPlaylist).where(
        UserPlaylist.id == playlist_id,
        UserPlaylist.user_id == user_id,
    )
    res = await db.exec(stmt)
    playlist = res.first()
    if not playlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Плейлист не найден",
        )
    return playlist


def _serialize_playlist(
    playlist: UserPlaylist,
    tracks: list[UserPlaylistTrack],
) -> UserPlaylistRead:
    assert playlist.id is not None
    covers: list[str] = []
    total_duration = 0
    for tr in tracks:
        total_duration += tr.duration
        if tr.cover and len(covers) < 4:
            covers.append(tr.cover)

    return UserPlaylistRead(
        id=playlist.id,
        name=playlist.name,
        tracks_count=len(tracks),
        duration=total_duration,
        covers=covers,
        created_at=playlist.created_at,
        updated_at=playlist.updated_at,
    )


async def _build_playlist_read(
    db: AsyncSession,
    playlist: UserPlaylist,
) -> UserPlaylistRead:
    assert playlist.id is not None
    stmt = (
        select(UserPlaylistTrack)
        .where(UserPlaylistTrack.playlist_id == playlist.id)
        .order_by(UserPlaylistTrack.position.asc(), UserPlaylistTrack.id.asc())  # type: ignore[attr-defined,union-attr]
    )
    res = await db.exec(stmt)
    tracks = list(res.all())
    return _serialize_playlist(playlist, tracks)


async def _resolve_track_snapshot(
    db: AsyncSession,
    user: User,
    ref: TrackRef,
) -> tuple[str, str, str, str, str | None, int]:
    srv = ref.service.strip().lower()
    sid = ref.service_id.strip()
    if not srv or not sid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Не указан сервис или идентификатор трека",
        )

    title = ref.title.strip() if ref.title and ref.title.strip() else None
    artist = ref.artist.strip() if ref.artist and ref.artist.strip() else None
    cover = ref.cover.strip() if ref.cover and ref.cover.strip() else None
    duration = ref.duration if ref.duration is not None else 0

    if not title or not artist or not cover or not duration:
        try:
            user_adapter = await get_user_adapter(db, user, srv)
            t_dto = await aggregator.get_track(srv, sid, adapter=user_adapter)
            if t_dto:
                title = title or t_dto.title
                artist = artist or t_dto.artist_display
                cover = cover or (str(t_dto.artwork_url) if t_dto.artwork_url else None)
                duration = duration or t_dto.duration_seconds
        except Exception as e:  # noqa: BLE001
            logger.warning("Could not fetch metadata for playlist track %s:%s: %s", srv, sid, e)

    return (
        srv,
        sid,
        title or f"Track {sid}",
        artist or "Неизвестный исполнитель",
        cover,
        duration,
    )


@router.get("", response_model=list[UserPlaylistRead])
async def list_playlists(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[UserPlaylistRead]:
    """List user's custom playlists with track count, total duration, and up to 4 cover URLs."""
    assert current_user.id is not None
    stmt = (
        select(UserPlaylist)
        .where(UserPlaylist.user_id == current_user.id)
        .order_by(UserPlaylist.created_at.desc(), UserPlaylist.id.desc())  # type: ignore[attr-defined,union-attr]
    )
    res = await db.exec(stmt)
    playlists = list(res.all())
    if not playlists:
        return []

    playlist_ids = [p.id for p in playlists if p.id is not None]
    tracks_stmt = (
        select(UserPlaylistTrack)
        .where(UserPlaylistTrack.playlist_id.in_(playlist_ids))  # type: ignore[attr-defined]
        .order_by(UserPlaylistTrack.position.asc(), UserPlaylistTrack.id.asc())  # type: ignore[attr-defined,union-attr]
    )
    tracks_res = await db.exec(tracks_stmt)
    tracks_by_playlist: dict[int, list[UserPlaylistTrack]] = {}
    for tr in tracks_res.all():
        tracks_by_playlist.setdefault(tr.playlist_id, []).append(tr)

    return [_serialize_playlist(p, tracks_by_playlist.get(p.id or 0, [])) for p in playlists]


@router.post("", response_model=UserPlaylistRead, status_code=status.HTTP_201_CREATED)
async def create_playlist(
    req: PlaylistCreateRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserPlaylistRead:
    """Create a new custom playlist for the current user."""
    assert current_user.id is not None
    cleaned_name, normalized_name = _normalize_playlist_name(req.name)
    await _ensure_unique_name(db, current_user.id, cleaned_name, normalized_name)

    playlist = UserPlaylist(
        user_id=current_user.id,
        name=cleaned_name,
        normalized_name=normalized_name,
    )
    db.add(playlist)
    await db.flush()
    assert playlist.id is not None

    seen_keys: set[tuple[str, str]] = set()
    position = 0
    for ref in req.tracks:
        srv, sid, title, artist, cover, duration = await _resolve_track_snapshot(db, current_user, ref)
        key = (srv, sid)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        db.add(
            UserPlaylistTrack(
                playlist_id=playlist.id,
                position=position,
                service=srv,
                service_id=sid,
                title=title,
                artist=artist,
                cover=cover,
                duration=duration,
            )
        )
        position += 1

    await db.commit()
    await db.refresh(playlist)
    return await _build_playlist_read(db, playlist)


@router.patch("/{playlist_id}", response_model=UserPlaylistRead)
async def rename_playlist(
    playlist_id: int,
    req: PlaylistUpdateRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserPlaylistRead:
    """Rename a user's custom playlist."""
    assert current_user.id is not None
    playlist = await _get_owned_playlist(db, current_user.id, playlist_id)
    cleaned_name, normalized_name = _normalize_playlist_name(req.name)
    await _ensure_unique_name(
        db,
        current_user.id,
        cleaned_name,
        normalized_name,
        exclude_playlist_id=playlist_id,
    )

    playlist.name = cleaned_name
    playlist.normalized_name = normalized_name
    playlist.updated_at = datetime.now(UTC)
    db.add(playlist)
    await db.commit()
    await db.refresh(playlist)
    return await _build_playlist_read(db, playlist)


@router.delete("/{playlist_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_playlist(
    playlist_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    """Delete a user's custom playlist and all its tracks."""
    assert current_user.id is not None
    playlist = await _get_owned_playlist(db, current_user.id, playlist_id)
    await db.exec(delete(UserPlaylistTrack).where(col(UserPlaylistTrack.playlist_id) == playlist_id))
    await db.delete(playlist)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{playlist_id}/tracks", response_model=list[TrackRead])
async def get_playlist_tracks(
    playlist_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> list[TrackRead]:
    """Get tracks of a user's custom playlist in order of addition."""
    assert current_user.id is not None
    await _get_owned_playlist(db, current_user.id, playlist_id)

    stmt = (
        select(UserPlaylistTrack)
        .where(UserPlaylistTrack.playlist_id == playlist_id)
        .order_by(UserPlaylistTrack.position.asc(), UserPlaylistTrack.id.asc())  # type: ignore[attr-defined,union-attr]
        .offset(offset)
        .limit(limit)
    )
    res = await db.exec(stmt)
    rows = list(res.all())
    if not rows:
        return []

    liked_keys = await _get_user_liked_keys(db, current_user.id)

    local_ids = [int(r.service_id) for r in rows if r.service == Service.LOCAL.value and r.service_id.isdigit()]
    local_uploads: dict[int, UserUpload] = {}
    if local_ids:
        up_res = await db.exec(
            select(UserUpload).where(
                UserUpload.user_id == current_user.id,
                col(UserUpload.id).in_(local_ids),
            )
        )
        local_uploads = {u.id: u for u in up_res.all() if u.id is not None}

    tracks_out: list[TrackRead] = []
    for row in rows:
        srv = row.service.lower()
        key = f"{srv}:{row.service_id}"
        numeric_id = abs(hash(key)) % 10_000_000 + 1
        source_code = _get_source_code(srv)
        is_liked = (srv, row.service_id) in liked_keys

        stream_url: str | None = None
        cover = row.cover or ""
        title = row.title
        artist = row.artist
        duration = row.duration

        if srv == Service.LOCAL.value and row.service_id.isdigit():
            upload = local_uploads.get(int(row.service_id))
            if upload and upload.id is not None:
                sig = create_stream_signature(upload.id, upload.user_id)
                stream_url = f"/api/uploads/{upload.id}/stream?sig={sig}"
                cover = upload.cover_template or (f"/api/uploads/{upload.id}/cover" if upload.cover_file else cover)
                title = upload.title
                artist = upload.artist
                duration = upload.duration_seconds
        elif srv == Service.YANDEX.value:
            stream_url = _yandex_proxy_url(srv, row.service_id, current_user.id)

        tracks_out.append(
            TrackRead(
                id=numeric_id,
                track_key=key,
                service=srv,
                service_id=row.service_id,
                title=title,
                artist=artist,
                artists=[artist] if artist else [],
                cover=cover,
                artwork_url=cover or None,
                duration=duration,
                duration_ms=duration * 1000,
                sources=[source_code],
                source=source_code,
                is_playable=True,
                liked=is_liked,
                direct_audio_url=stream_url,
                stream_url=stream_url,
                playback=PlaybackInfo(
                    kind="direct_url",
                    ref=stream_url,
                    direct_audio_url=stream_url,
                ) if stream_url else None,
            )
        )

    return tracks_out


@router.post("/{playlist_id}/tracks", response_model=UserPlaylistRead)
async def add_track_to_playlist(
    playlist_id: int,
    ref: TrackRef,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserPlaylistRead:
    """Add a track to a user's custom playlist (idempotent)."""
    assert current_user.id is not None
    playlist = await _get_owned_playlist(db, current_user.id, playlist_id)

    srv = ref.service.strip().lower()
    sid = ref.service_id.strip()
    if not srv or not sid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Не указан сервис или идентификатор трека",
        )

    existing_stmt = select(UserPlaylistTrack).where(
        UserPlaylistTrack.playlist_id == playlist_id,
        UserPlaylistTrack.service == srv,
        UserPlaylistTrack.service_id == sid,
    )
    existing_res = await db.exec(existing_stmt)
    if existing_res.first():
        return await _build_playlist_read(db, playlist)

    _, _, title, artist, cover, duration = await _resolve_track_snapshot(db, current_user, ref)

    max_pos_stmt = select(func.max(UserPlaylistTrack.position)).where(
        UserPlaylistTrack.playlist_id == playlist_id
    )
    max_pos_res = await db.exec(max_pos_stmt)
    max_pos = max_pos_res.first()
    next_pos = (max_pos + 1) if max_pos is not None else 0

    db.add(
        UserPlaylistTrack(
            playlist_id=playlist_id,
            position=next_pos,
            service=srv,
            service_id=sid,
            title=title,
            artist=artist,
            cover=cover,
            duration=duration,
        )
    )
    playlist.updated_at = datetime.now(UTC)
    db.add(playlist)
    await db.commit()
    await db.refresh(playlist)
    return await _build_playlist_read(db, playlist)


@router.delete("/{playlist_id}/tracks/{service}/{service_id}", response_model=UserPlaylistRead)
async def remove_track_from_playlist(
    playlist_id: int,
    service: str,
    service_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserPlaylistRead:
    """Remove a track from a user's custom playlist."""
    assert current_user.id is not None
    playlist = await _get_owned_playlist(db, current_user.id, playlist_id)

    stmt = select(UserPlaylistTrack).where(
        UserPlaylistTrack.playlist_id == playlist_id,
        UserPlaylistTrack.service == service.strip().lower(),
        UserPlaylistTrack.service_id == service_id,
    )
    res = await db.exec(stmt)
    track = res.first()
    if track:
        await db.delete(track)
        playlist.updated_at = datetime.now(UTC)
        db.add(playlist)
        await db.commit()
        await db.refresh(playlist)

    return await _build_playlist_read(db, playlist)
