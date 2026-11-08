from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.deps import get_current_active_user, get_optional_current_user
from app.database import get_db
from app.models.playlist import Playlist, PlaylistTrack
from app.models.user import User
from app.schemas.playlist import (
    PlaylistCreate,
    PlaylistRead,
    PlaylistReorder,
    PlaylistTrackAdd,
    PlaylistTrackRead,
    PlaylistUpdate,
)

router = APIRouter(prefix="/api/playlists", tags=["playlists"])


@router.get("", response_model=list[PlaylistRead])
@router.get("/", response_model=list[PlaylistRead], include_in_schema=False)
async def list_playlists(
    current_user: Annotated[User | None, Depends(get_optional_current_user)] = None,
    db: AsyncSession = Depends(get_db),
) -> list[PlaylistRead]:
    if not current_user or not current_user.id:
        # Return public playlists for guests
        stmt = select(Playlist).where(Playlist.is_public == True)  # noqa: E712
        res = await db.exec(stmt)
        playlists = res.all()
    else:
        # User playlists + public playlists
        stmt = select(Playlist).where(
            (Playlist.user_id == current_user.id) | (Playlist.is_public == True)  # noqa: E712
        ).order_by(Playlist.updated_at.desc())
        res = await db.exec(stmt)
        playlists = res.all()

    result = []
    for p in playlists:
        assert p.id is not None
        # Count tracks
        count_stmt = select(PlaylistTrack).where(PlaylistTrack.playlist_id == p.id)
        count_res = await db.exec(count_stmt)
        tracks = count_res.all()

        result.append(
            PlaylistRead(
                id=p.id,
                name=p.name,
                description=p.description,
                cover=p.cover_url or "",
                tracks_count=len(tracks),
                is_public=p.is_public,
                created_at=p.created_at,
                updated_at=p.updated_at,
            )
        )
    return result


@router.post("", response_model=PlaylistRead, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=PlaylistRead, status_code=status.HTTP_201_CREATED, include_in_schema=False)
async def create_playlist(
    payload: PlaylistCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> PlaylistRead:
    assert current_user.id is not None
    playlist = Playlist(
        user_id=current_user.id,
        name=payload.name.strip(),
        description=payload.description.strip() if payload.description else None,
        cover_url=payload.cover_url,
        is_public=payload.is_public,
    )
    db.add(playlist)
    await db.commit()
    await db.refresh(playlist)

    assert playlist.id is not None
    return PlaylistRead(
        id=playlist.id,
        name=playlist.name,
        description=playlist.description,
        cover=playlist.cover_url or "",
        tracks_count=0,
        is_public=playlist.is_public,
        created_at=playlist.created_at,
        updated_at=playlist.updated_at,
    )


@router.get("/{playlist_id}", response_model=PlaylistRead)
async def get_playlist(
    playlist_id: int,
    current_user: Annotated[User | None, Depends(get_optional_current_user)] = None,
    db: AsyncSession = Depends(get_db),
) -> PlaylistRead:
    stmt = select(Playlist).where(Playlist.id == playlist_id)
    res = await db.exec(stmt)
    playlist = res.first()
    if not playlist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Playlist not found")

    if not playlist.is_public:
        if not current_user or playlist.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    # Load tracks ordered by position
    track_stmt = (
        select(PlaylistTrack)
        .where(PlaylistTrack.playlist_id == playlist_id)
        .order_by(PlaylistTrack.position.asc(), PlaylistTrack.created_at.asc())
    )
    track_res = await db.exec(track_stmt)
    raw_tracks = track_res.all()

    tracks_read = [
        PlaylistTrackRead(
            id=t.id or 0,
            playlist_id=t.playlist_id,
            service=t.service,
            service_id=t.service_id,
            title=t.title,
            artist=t.artist,
            album=t.album,
            cover=t.cover_url or "",
            duration=t.duration,
            position=t.position,
            playback_kind=t.playback_kind,
            playback_ref=t.playback_ref,
            created_at=t.created_at,
        )
        for t in raw_tracks
    ]

    return PlaylistRead(
        id=playlist.id or playlist_id,
        name=playlist.name,
        description=playlist.description,
        cover=playlist.cover_url or "",
        tracks_count=len(tracks_read),
        is_public=playlist.is_public,
        tracks=tracks_read,
        created_at=playlist.created_at,
        updated_at=playlist.updated_at,
    )


@router.put("/{playlist_id}", response_model=PlaylistRead)
async def update_playlist(
    playlist_id: int,
    payload: PlaylistUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> PlaylistRead:
    stmt = select(Playlist).where(Playlist.id == playlist_id)
    res = await db.exec(stmt)
    playlist = res.first()
    if not playlist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Playlist not found")
    if playlist.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    if payload.name is not None:
        playlist.name = payload.name.strip()
    if payload.description is not None:
        playlist.description = payload.description.strip()
    if payload.cover_url is not None:
        playlist.cover_url = payload.cover_url
    if payload.is_public is not None:
        playlist.is_public = payload.is_public

    db.add(playlist)
    await db.commit()
    await db.refresh(playlist)

    return await get_playlist(playlist_id=playlist_id, current_user=current_user, db=db)


@router.delete("/{playlist_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_playlist(
    playlist_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> None:
    stmt = select(Playlist).where(Playlist.id == playlist_id)
    res = await db.exec(stmt)
    playlist = res.first()
    if not playlist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Playlist not found")
    if playlist.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    # Delete all tracks in playlist
    track_stmt = select(PlaylistTrack).where(PlaylistTrack.playlist_id == playlist_id)
    track_res = await db.exec(track_stmt)
    for t in track_res.all():
        await db.delete(t)

    await db.delete(playlist)
    await db.commit()


@router.post("/{playlist_id}/tracks", response_model=PlaylistTrackRead, status_code=status.HTTP_201_CREATED)
async def add_track_to_playlist(
    playlist_id: int,
    payload: PlaylistTrackAdd,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> PlaylistTrackRead:
    stmt = select(Playlist).where(Playlist.id == playlist_id)
    res = await db.exec(stmt)
    playlist = res.first()
    if not playlist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Playlist not found")
    if playlist.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    # Determine next position
    pos_stmt = (
        select(PlaylistTrack.position)
        .where(PlaylistTrack.playlist_id == playlist_id)
        .order_by(PlaylistTrack.position.desc())
        .limit(1)
    )
    pos_res = await db.exec(pos_stmt)
    last_pos = pos_res.first()
    next_pos = (last_pos + 1) if last_pos is not None else 0

    track = PlaylistTrack(
        playlist_id=playlist_id,
        service=payload.service,
        service_id=payload.service_id,
        title=payload.title,
        artist=payload.artist,
        album=payload.album,
        cover_url=payload.cover_url,
        duration=payload.duration,
        position=next_pos,
        playback_kind=payload.playback_kind,
        playback_ref=payload.playback_ref,
    )
    db.add(track)
    await db.commit()
    await db.refresh(track)

    assert track.id is not None
    return PlaylistTrackRead(
        id=track.id,
        playlist_id=track.playlist_id,
        service=track.service,
        service_id=track.service_id,
        title=track.title,
        artist=track.artist,
        album=track.album,
        cover=track.cover_url or "",
        duration=track.duration,
        position=track.position,
        playback_kind=track.playback_kind,
        playback_ref=track.playback_ref,
        created_at=track.created_at,
    )


@router.delete("/{playlist_id}/tracks/{track_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_track_from_playlist(
    playlist_id: int,
    track_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> None:
    stmt = select(Playlist).where(Playlist.id == playlist_id)
    res = await db.exec(stmt)
    playlist = res.first()
    if not playlist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Playlist not found")
    if playlist.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    track_stmt = select(PlaylistTrack).where(
        PlaylistTrack.id == track_id,
        PlaylistTrack.playlist_id == playlist_id,
    )
    track_res = await db.exec(track_stmt)
    track = track_res.first()
    if not track:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Track not found in playlist")

    await db.delete(track)
    await db.commit()


@router.put("/{playlist_id}/reorder", response_model=PlaylistRead)
async def reorder_playlist_tracks(
    playlist_id: int,
    payload: PlaylistReorder,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> PlaylistRead:
    stmt = select(Playlist).where(Playlist.id == playlist_id)
    res = await db.exec(stmt)
    playlist = res.first()
    if not playlist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Playlist not found")
    if playlist.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    track_stmt = select(PlaylistTrack).where(PlaylistTrack.playlist_id == playlist_id)
    track_res = await db.exec(track_stmt)
    track_map = {t.id: t for t in track_res.all()}

    for new_pos, t_id in enumerate(payload.track_ids):
        if t_id in track_map:
            track_map[t_id].position = new_pos
            db.add(track_map[t_id])

    await db.commit()
    return await get_playlist(playlist_id=playlist_id, current_user=current_user, db=db)
