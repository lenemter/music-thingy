from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.config import settings

from .base import BaseMusicAdapter
from .dto import (
    CODE_TO_SERVICE_MAP,
    SERVICE_CODE_MAP,
    SERVICE_NAME_MAP,
    AlbumDTO,
    ArtistDTO,
    ErrorKind,
    PlaylistDTO,
    SearchResultDTO,
    SearchType,
    Service,
    ServiceErrorDTO,
    TrackDTO,
)
from .yandex import YandexMusicAdapter

log = logging.getLogger(__name__)


class MusicAggregator:
    """Aggregates searches and track/media retrieval across music services.

    Supports dynamic adapter registration. By default, initializes available
    adapters (e.g. Yandex Music) while exposing clean statuses for all platforms.
    """

    def __init__(self) -> None:
        self._adapters: dict[Service, BaseMusicAdapter] = {}
        self._init_adapters()

    def _init_adapters(self) -> None:
        # Initialize Yandex Music adapter
        try:
            self._adapters[Service.YANDEX] = YandexMusicAdapter(token=settings.YANDEX_MUSIC_TOKEN)
            log.info("YandexMusicAdapter initialized successfully.")
        except Exception as e:
            log.warning("Could not initialize Yandex adapter: %s", e)

    def register_adapter(self, adapter: BaseMusicAdapter) -> None:
        """Register an adapter for a service dynamically."""
        self._adapters[adapter.service] = adapter
        log.info("Registered adapter for %s", adapter.service)

    def unregister_adapter(self, service: Service) -> None:
        """Unregister an adapter for a service."""
        if service in self._adapters:
            del self._adapters[service]

    def get_adapter(self, service: Service | str) -> BaseMusicAdapter | None:
        if isinstance(service, str):
            resolved = CODE_TO_SERVICE_MAP.get(service.lower(), CODE_TO_SERVICE_MAP.get(service))
            if not resolved:
                return None
            service = resolved
        return self._adapters.get(service)

    def is_service_online(self, service: Service | str) -> bool:
        return self.get_adapter(service) is not None

    def get_services_status(self, enabled_services: set[str] | None = None) -> list[dict[str, Any]]:
        """Returns the list of supported services and their availability status matching frontend `Service[]`."""
        all_supported = [
            (Service.YANDEX, "ЯМ", "Яндекс Музыка", "Яндекс"),
            (Service.SPOTIFY, "SP", "Spotify", "Spotify"),
            (Service.SOUNDCLOUD, "SC", "SoundCloud", "SoundCloud"),
            (Service.YOUTUBE, "YT", "YouTube", "YouTube"),
        ]

        result = []
        for s_enum, code, name, short_name in all_supported:
            adapter = self._adapters.get(s_enum)
            is_online = adapter is not None
            if enabled_services is not None:
                is_online = is_online and (code in enabled_services or s_enum.value in enabled_services)

            result.append({
                "code": code,
                "name": name,
                "shortName": short_name,
                "service": s_enum.value,
                "online": is_online,
            })
        return result

    async def search(
        self,
        query: str,
        services: list[Service | str] | None = None,
        types: frozenset[SearchType] = frozenset({SearchType.TRACK}),
        limit_per_service: int = 10,
    ) -> SearchResultDTO:
        # If no specific services requested, try all supported services
        if not services:
            services = [Service.YANDEX, Service.SPOTIFY, Service.SOUNDCLOUD, Service.YOUTUBE]

        # Resolve requested services
        target_services: list[Service] = []
        missing_services: list[Service] = []
        for s in services:
            resolved = s if isinstance(s, Service) else CODE_TO_SERVICE_MAP.get(s.lower(), CODE_TO_SERVICE_MAP.get(s))
            if not resolved:
                continue
            if resolved in self._adapters and resolved not in target_services:
                target_services.append(resolved)
            elif resolved not in self._adapters and resolved not in missing_services:
                missing_services.append(resolved)

        async def _query_service(srv: Service) -> SearchResultDTO:
            adapter = self._adapters[srv]
            try:
                return await asyncio.to_thread(adapter.search, query, types, limit_per_service)
            except Exception as e:
                log.warning("Search failed for service %s: %s", srv, e)
                return SearchResultDTO(
                    query=query,
                    errors=(ServiceErrorDTO(service=srv, kind=ErrorKind.UNAVAILABLE, message=str(e)),),
                )

        tasks = [_query_service(s) for s in target_services]
        results = await asyncio.gather(*tasks, return_exceptions=False) if tasks else []

        all_tracks: list[TrackDTO] = []
        all_artists: list[ArtistDTO] = []
        all_albums: list[AlbumDTO] = []
        all_playlists: list[PlaylistDTO] = []
        all_errors: list[ServiceErrorDTO] = []

        # Record missing adapter errors
        for m in missing_services:
            all_errors.append(
                ServiceErrorDTO(
                    service=m,
                    kind=ErrorKind.NOT_SUPPORTED,
                    message=f"Адаптер для сервиса {m.value} ещё не подключён или недоступен",
                )
            )

        for r in results:
            all_tracks.extend(r.tracks)
            all_artists.extend(r.artists)
            all_albums.extend(r.albums)
            all_playlists.extend(r.playlists)
            all_errors.extend(r.errors)

        merged_tracks = self._aggregate_tracks(all_tracks)

        return SearchResultDTO(
            query=query,
            tracks=tuple(merged_tracks),
            artists=tuple(all_artists),
            albums=tuple(all_albums),
            playlists=tuple(all_playlists),
            errors=tuple(all_errors),
        )

    def _aggregate_tracks(self, tracks: list[TrackDTO]) -> list[TrackDTO]:
        """Groups matching tracks across services to combine `sources` tags (e.g. ['ЯМ', 'SP'])."""
        by_key: dict[str, list[TrackDTO]] = {}
        for t in tracks:
            norm_title = "".join(ch for ch in t.title.lower() if ch.isalnum() or ch.isspace()).strip()
            norm_artist = "".join(ch for ch in t.artist_display.lower() if ch.isalnum() or ch.isspace()).strip()
            key = f"{norm_title}::{norm_artist}"
            by_key.setdefault(key, []).append(t)

        merged: list[TrackDTO] = []
        for _, group in by_key.items():
            primary = group[0]
            sources: list[str] = []
            for item in group:
                code = SERVICE_CODE_MAP.get(item.service, str(item.service.value).upper()[:2])
                if code not in sources:
                    sources.append(code)

            updated = TrackDTO(
                service=primary.service,
                service_id=primary.service_id,
                title=primary.title,
                artists=primary.artists,
                is_playable=primary.is_playable,
                artist_ids=primary.artist_ids,
                duration_ms=primary.duration_ms,
                album=primary.album,
                playback=primary.playback,
                direct_audio_url=primary.direct_audio_url,
                external_url=primary.external_url,
                artwork_url=primary.artwork_url,
                sources=tuple(sources),
                edited=primary.edited,
                liked=primary.liked,
            )
            merged.append(updated)

        return merged

    async def get_track(self, service: Service | str, service_id: str) -> TrackDTO | None:
        adapter = self.get_adapter(service)
        if not adapter:
            return None
        return await asyncio.to_thread(adapter.get_track, service_id)

    async def get_album(self, service: Service | str, service_id: str) -> AlbumDTO | None:
        adapter = self.get_adapter(service)
        if not adapter:
            return None
        return await asyncio.to_thread(adapter.get_album, service_id)

    async def get_artist(self, service: Service | str, service_id: str) -> ArtistDTO | None:
        adapter = self.get_adapter(service)
        if not adapter:
            return None
        return await asyncio.to_thread(adapter.get_artist, service_id)

    async def get_playlist(self, service: Service | str, service_id: str) -> PlaylistDTO | None:
        adapter = self.get_adapter(service)
        if not adapter:
            return None
        return await asyncio.to_thread(adapter.get_playlist, service_id)


aggregator = MusicAggregator()
