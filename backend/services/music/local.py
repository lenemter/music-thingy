from __future__ import annotations

"""Адаптер локальных файлов: аудио, которые пользователь сам загрузил (/api/uploads).

Адаптер не ходит в БД и на диск: ему передают готовый список загрузок пользователя
(см. LocalUpload), поэтому создаётся он на каждый запрос и подставляется в
aggregator.search(user_adapters={Service.LOCAL: adapter}).

Форматы service_id:
    трек      "{upload_id}" (числовой id записи UserUpload, как в /api/uploads)
    плейлист, артист, альбом  не поддерживаются
"""
from collections.abc import Iterable
from dataclasses import dataclass
from typing import ClassVar

from .base import BaseMusicAdapter
from .dto import (
    ArtistDTO,
    PlaybackDTO,
    PlaybackKind,
    PlaylistDTO,
    SearchResultDTO,
    SearchType,
    Service,
    TrackDTO,
)


@dataclass(frozen=True, slots=True)
class LocalUpload:
    """Минимум данных о загрузке, нужный адаптеру (не зависит от ORM-модели)."""

    id: int
    title: str
    artist: str
    duration_seconds: int
    audio_url: str  # готовая (подписанная) ссылка на /api/uploads/{id}/stream
    cover: str | None = None  # URL обложки или "template:N"


def _to_track(u: LocalUpload) -> TrackDTO:
    return TrackDTO(
        service=Service.LOCAL,
        service_id=str(u.id),
        title=u.title,
        artists=(u.artist,) if u.artist else (),
        is_playable=True,
        duration_ms=u.duration_seconds * 1000 if u.duration_seconds > 0 else None,
        playback=PlaybackDTO(kind=PlaybackKind.DIRECT_URL, ref=u.audio_url),
        direct_audio_url=u.audio_url,
        artwork_url=u.cover,
    )


class LocalFilesAdapter(BaseMusicAdapter):
    service: ClassVar[Service] = Service.LOCAL
    official: ClassVar[bool] = False

    def __init__(self, uploads: Iterable[LocalUpload]) -> None:
        self._tracks: dict[str, TrackDTO] = {str(u.id): _to_track(u) for u in uploads}

    def search(
        self,
        query: str,
        types: frozenset[SearchType] = frozenset({SearchType.TRACK}),
        limit: int = 10,
    ) -> SearchResultDTO:
        query = query.strip()
        # Альбомы, артисты и плейлисты для загрузок не поддерживаются: молча пропускаем,
        # потому что фронт по умолчанию запрашивает "track,album".
        if not query or limit <= 0 or SearchType.TRACK not in types:
            return SearchResultDTO(query=query)

        tokens = query.casefold().split()
        found = [
            t for t in self._tracks.values()
            if all(tok in f"{t.title} {' '.join(t.artists)}".casefold() for tok in tokens)
        ]
        return SearchResultDTO(query=query, tracks=tuple(found[:limit]))

    def get_track(self, service_id: str) -> TrackDTO | None:
        return self._tracks.get(service_id.strip())

    def get_playlist(self, service_id: str) -> PlaylistDTO | None:
        return None

    def get_artist(self, service_id: str) -> ArtistDTO | None:
        return None

    def get_user_favorites(self, account_id: str | None = None, limit: int = 50) -> list[TrackDTO]:
        return []

    def set_track_like(self, service_id: str, liked: bool) -> bool:
        return True