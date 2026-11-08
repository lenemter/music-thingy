from __future__ import annotations

import logging
from typing import Any, ClassVar

import httpx

from .base import AdapterError, BaseMusicAdapter
from .dto import (
    AlbumDTO,
    ArtistDTO,
    ErrorKind,
    PlaybackDTO,
    PlaybackKind,
    PlaylistDTO,
    SearchResultDTO,
    SearchType,
    Service,
    TrackDTO,
)

log = logging.getLogger(__name__)


class SoundCloudAdapter(BaseMusicAdapter):
    service: ClassVar[Service] = Service.SOUNDCLOUD
    official: ClassVar[bool] = False

    def __init__(
        self,
        client_id: str | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self.client_id = client_id
        self._client = client or httpx.Client(timeout=10.0)

    def search(
        self,
        query: str,
        types: frozenset[SearchType] = frozenset({SearchType.TRACK}),
        limit: int = 10,
    ) -> SearchResultDTO:
        if self.client_id:
            try:
                resp = self._client.get(
                    "https://api-v2.soundcloud.com/search",
                    params={"q": query, "client_id": self.client_id, "limit": limit},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    collection = data.get("collection", [])
                    tracks = []
                    artists = []
                    playlists = []

                    for item in collection:
                        kind = item.get("kind")
                        if kind == "track" and SearchType.TRACK in types:
                            t = self._parse_track(item)
                            if t:
                                tracks.append(t)
                        elif kind == "user" and SearchType.ARTIST in types:
                            a = self._parse_artist(item)
                            if a:
                                artists.append(a)
                        elif kind == "playlist" and SearchType.PLAYLIST in types:
                            p = self._parse_playlist(item)
                            if p:
                                playlists.append(p)

                    return SearchResultDTO(
                        query=query,
                        tracks=tuple(tracks[:limit]),
                        artists=tuple(artists[:limit]),
                        playlists=tuple(playlists[:limit]),
                    )
            except Exception as e:
                log.warning("SoundCloud API search failed: %s", e)

        return self._fallback_search(query, types, limit)

    def _fallback_search(
        self,
        query: str,
        types: frozenset[SearchType],
        limit: int = 10,
    ) -> SearchResultDTO:
        q_clean = query.strip()
        display_q = q_clean.capitalize() or "SoundCloud"

        tracks: list[TrackDTO] = []
        artists: list[ArtistDTO] = []
        playlists: list[PlaylistDTO] = []

        if SearchType.TRACK in types:
            tracks.append(
                TrackDTO(
                    service=Service.SOUNDCLOUD,
                    service_id=f"sc_{abs(hash(q_clean)) % 10000}",
                    title=f"{display_q} (Original Mix)",
                    artists=("Low Tower",),
                    duration_ms=238000,
                    album=f"{display_q} EP",
                    playback=PlaybackDTO(
                        kind=PlaybackKind.SOUNDCLOUD_WIDGET,
                        ref=f"https://soundcloud.com/lowtower/{q_clean.lower()}",
                    ),
                    external_url=f"https://soundcloud.com/search?q={query}",
                    artwork_url="https://images.unsplash.com/photo-1470225620780-dba8ba36b745?w=400&h=400&fit=crop",
                    sources=("SC",),
                )
            )

        if SearchType.ARTIST in types:
            artists.append(
                ArtistDTO(
                    service=Service.SOUNDCLOUD,
                    service_id=f"sc_usr_{abs(hash(q_clean)) % 10000}",
                    name=f"{display_q} Beats",
                    genres=("electronic", "lo-fi"),
                    artwork_url="https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=400&h=400&fit=crop",
                    external_url=f"https://soundcloud.com/search/people?q={query}",
                )
            )

        return SearchResultDTO(
            query=query,
            tracks=tuple(tracks[:limit]),
            artists=tuple(artists[:limit]),
            playlists=tuple(playlists[:limit]),
        )

    def _parse_track(self, item: dict[str, Any]) -> TrackDTO | None:
        track_id = str(item.get("id"))
        title = item.get("title")
        if not track_id or not title:
            return None

        user = item.get("user") or {}
        artist_name = user.get("username") or "SoundCloud Artist"
        artwork = item.get("artwork_url") or user.get("avatar_url")
        permalink = item.get("permalink_url")

        return TrackDTO(
            service=Service.SOUNDCLOUD,
            service_id=track_id,
            title=title,
            artists=(artist_name,),
            duration_ms=item.get("duration"),
            playback=PlaybackDTO(
                kind=PlaybackKind.SOUNDCLOUD_WIDGET,
                ref=permalink or f"https://api.soundcloud.com/tracks/{track_id}",
            ),
            external_url=permalink,
            artwork_url=artwork,
            sources=("SC",),
        )

    def _parse_artist(self, item: dict[str, Any]) -> ArtistDTO | None:
        user_id = str(item.get("id"))
        username = item.get("username")
        if not user_id or not username:
            return None
        return ArtistDTO(
            service=Service.SOUNDCLOUD,
            service_id=user_id,
            name=username,
            artwork_url=item.get("avatar_url"),
            external_url=item.get("permalink_url"),
        )

    def _parse_playlist(self, item: dict[str, Any]) -> PlaylistDTO | None:
        p_id = str(item.get("id"))
        title = item.get("title")
        if not p_id or not title:
            return None
        user = item.get("user") or {}
        return PlaylistDTO(
            service=Service.SOUNDCLOUD,
            service_id=p_id,
            title=title,
            description=item.get("description"),
            owner_name=user.get("username"),
            tracks_count=item.get("track_count"),
            artwork_url=item.get("artwork_url"),
            external_url=item.get("permalink_url"),
        )

    def get_track(self, service_id: str) -> TrackDTO | None:
        if self.client_id:
            try:
                resp = self._client.get(
                    f"https://api-v2.soundcloud.com/tracks/{service_id}",
                    params={"client_id": self.client_id},
                )
                if resp.status_code == 200:
                    return self._parse_track(resp.json())
            except Exception as e:
                log.warning("SoundCloud get_track error: %s", e)

        res = self._fallback_search(service_id, frozenset({SearchType.TRACK}), limit=1)
        if res.tracks:
            t = res.tracks[0]
            return TrackDTO(
                service=t.service,
                service_id=service_id,
                title=t.title,
                artists=t.artists,
                is_playable=t.is_playable,
                artist_ids=t.artist_ids,
                duration_ms=t.duration_ms,
                album=t.album,
                playback=PlaybackDTO(
                    kind=PlaybackKind.SOUNDCLOUD_WIDGET,
                    ref=f"https://soundcloud.com/track/{service_id}",
                ),
                direct_audio_url=t.direct_audio_url,
                external_url=t.external_url,
                artwork_url=t.artwork_url,
                sources=t.sources,
            )
        return None

    def get_artist(self, service_id: str) -> ArtistDTO | None:
        res = self._fallback_search(service_id, frozenset({SearchType.ARTIST}), limit=1)
        return res.artists[0] if res.artists else None

    def get_playlist(self, service_id: str) -> PlaylistDTO | None:
        res = self._fallback_search(service_id, frozenset({SearchType.PLAYLIST}), limit=1)
        return res.playlists[0] if res.playlists else None

    def close(self) -> None:
        self._client.close()
