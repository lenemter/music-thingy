from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.deps import get_current_active_user, get_optional_current_user
from app.database import get_db
from app.models.history import ListeningHistory
from app.models.user import User
from app.schemas.history import ListeningHistoryCreate, ListeningHistoryRead
from app.schemas.music import AlbumRead

router = APIRouter(prefix="/api/history", tags=["history"])


@router.post("", response_model=ListeningHistoryRead, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=ListeningHistoryRead, status_code=status.HTTP_201_CREATED, include_in_schema=False)
async def record_playback(
    payload: ListeningHistoryCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> ListeningHistoryRead:
    assert current_user.id is not None
    entry = ListeningHistory(
        user_id=current_user.id,
        service=payload.service.lower(),
        service_id=payload.service_id,
        title=payload.title,
        artist=payload.artist,
        album=payload.album,
        cover_url=payload.cover_url,
        duration=payload.duration,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)

    assert entry.id is not None
    return ListeningHistoryRead(
        id=entry.id,
        service=entry.service,
        service_id=entry.service_id,
        title=entry.title,
        artist=entry.artist,
        album=entry.album,
        cover=entry.cover_url or "",
        duration=entry.duration,
        listened_at=entry.listened_at,
    )


@router.get("", response_model=list[ListeningHistoryRead])
@router.get("/", response_model=list[ListeningHistoryRead], include_in_schema=False)
async def get_history(
    current_user: Annotated[User, Depends(get_current_active_user)],
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[ListeningHistoryRead]:
    assert current_user.id is not None
    stmt = (
        select(ListeningHistory)
        .where(ListeningHistory.user_id == current_user.id)
        .order_by(ListeningHistory.listened_at.desc())
        .limit(limit)
    )
    res = await db.exec(stmt)
    entries = res.all()

    return [
        ListeningHistoryRead(
            id=e.id or 1,
            service=e.service,
            service_id=e.service_id,
            title=e.title,
            artist=e.artist,
            album=e.album,
            cover=e.cover_url or "",
            duration=e.duration,
            listened_at=e.listened_at,
        )
        for e in entries
    ]


@router.get("/albums", response_model=list[AlbumRead])
async def get_continue_listening_albums(
    current_user: Annotated[User | None, Depends(get_optional_current_user)] = None,
    limit: int = Query(6, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
) -> list[AlbumRead]:
    """Returns recent albums for the 'Продолжить слушать' widget."""
    albums_found: list[AlbumRead] = []

    if current_user and current_user.id:
        stmt = (
            select(ListeningHistory)
            .where(ListeningHistory.user_id == current_user.id, ListeningHistory.album != None)  # noqa: E711
            .order_by(ListeningHistory.listened_at.desc())
            .limit(limit * 3)
        )
        res = await db.exec(stmt)
        entries = res.all()

        seen_titles = set()
        for e in entries:
            if e.album and e.album not in seen_titles:
                seen_titles.add(e.album)
                albums_found.append(
                    AlbumRead(
                        id=e.id or 1,
                        service=e.service,
                        service_id=f"alb_{e.id}",
                        title=e.album,
                        subtitle=f"{e.artist} · альбом" if e.artist else "Альбом",
                        cover=e.cover_url or "",
                    )
                )
            if len(albums_found) >= limit:
                break

    # Curated fallbacks matching UI mocks if user has fewer entries
    fallbacks = [
        AlbumRead(id=1, service="spotify", service_id="fb_1", title="Ночные поездки", subtitle="Плейлист · 64 трека", cover=""),
        AlbumRead(id=2, service="spotify", service_id="fb_2", title="Солнцеворот", subtitle="Орбита 9 · альбом", cover=""),
        AlbumRead(id=3, service="yandex", service_id="fb_3", title="Три орбиты", subtitle="Станция Полночь · EP", cover=""),
        AlbumRead(id=4, service="soundcloud", service_id="fb_4", title="Бег сквозь лес", subtitle="Хвойный шум · альбом", cover=""),
        AlbumRead(id=5, service="yandex", service_id="fb_5", title="Сигнал 404", subtitle="Low Tower · альбом", cover=""),
    ]

    for fb in fallbacks:
        if len(albums_found) >= limit:
            break
        if not any(a.title == fb.title for a in albums_found):
            albums_found.append(fb)

    return albums_found[:limit]
