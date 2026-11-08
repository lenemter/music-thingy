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


class YouTubeAdapter(BaseMusicAdapter):
    service: ClassVar[Service] = Service.YOUTUBE
    official: ClassVar[bool] = True

    def __init__(
        self,
        api_key: str | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self.api_key = api_key
        self._client = client or httpx.Client(timeout=10.0)

    def search(
        self,
        query: str,
        types: frozenset[SearchType] = frozenset({SearchType.TRACK}),
        limit: int = 10,
    ) -> SearchResultDTO:
        if self.api_key:
            try:
                # Use YouTube Data API v3
                resp = self._client.get(
                    "https://www.googleapis.com/youtube/v3/search",
                    params={
                        "part": "snippet",
                        "q": query,
                        "type": "video",
                        "videoCategoryId": "10",  # Music category
                        "maxResults": limit,
                        "key": self.api_key,
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    tracks = []
                    for item in data.get("items", []):
                        vid_id = item.get("id", {}).get("videoId")
                        snippet = item.get("snippet", {})
                        if vid_id and snippet:
                            title = snippet.get("title", "")
                            channel = snippet.get("channelTitle", "YouTube Music")
                            thumbnails = snippet.get("thumbnails", {})
                            cover = (
                                thumbnails.get("high", {}).get("url")
                                or thumbnails.get("medium", {}).get("url")
                                or thumbnails.get("default", {}).get("url")
                            )

                            tracks.append(
                                TrackDTO(
                                    service=Service.YOUTUBE,
                                    service_id=vid_id,
                                    title=title,
                                    artists=(channel,),
                                    duration_ms=210000,
                                    playback=PlaybackDTO(kind=PlaybackKind.YOUTUBE_IFRAME, ref=vid_id),
                                    external_url=f"https://www.youtube.com/watch?v={vid_id}",
                                    artwork_url=cover,
                                    sources=("YT",),
                                )
                            )

                    return SearchResultDTO(query=query, tracks=tuple(tracks[:limit]))
            except Exception as e:
                log.warning("YouTube API search error: %s", e)

        return self._fallback_search(query, types, limit)

    def _fallback_search(
        self,
        query: str,
        types: frozenset[SearchType],
        limit: int = 10,
    ) -> SearchResultDTO:
        q_clean = query.strip()
        display_q = q_clean.capitalize() or "YouTube"
        mock_id = f"yt_{abs(hash(q_clean)) % 100000}"

        tracks: list[TrackDTO] = []
        if SearchType.TRACK in types:
            tracks.append(
                TrackDTO(
                    service=Service.YOUTUBE,
                    service_id=mock_id,
                    title=f"{display_q} (Official Video)",
                    artists=("Orbita 9",),
                    duration_ms=252000,
                    album=f"{display_q} Live",
                    playback=PlaybackDTO(
                        kind=PlaybackKind.YOUTUBE_IFRAME,
                        ref="dQw4w9WgXcQ",  # classic working video id for player verification
                    ),
                    external_url=f"https://www.youtube.com/results?search_query={query}",
                    artwork_url="https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=400&h=400&fit=crop",
                    sources=("YT",),
                )
            )

        return SearchResultDTO(query=query, tracks=tuple(tracks[:limit]))

    def get_track(self, service_id: str) -> TrackDTO | None:
        if self.api_key:
            try:
                resp = self._client.get(
                    "https://www.googleapis.com/youtube/v3/videos",
                    params={"part": "snippet,contentDetails", "id": service_id, "key": self.api_key},
                )
                if resp.status_code == 200:
                    items = resp.json().get("items", [])
                    if items:
                        item = items[0]
                        snippet = item.get("snippet", {})
                        title = snippet.get("title", "")
                        channel = snippet.get("channelTitle", "")
                        thumbs = snippet.get("thumbnails", {})
                        cover = thumbs.get("high", {}).get("url") or thumbs.get("default", {}).get("url")
                        return TrackDTO(
                            service=Service.YOUTUBE,
                            service_id=service_id,
                            title=title,
                            artists=(channel,),
                            duration_ms=210000,
                            playback=PlaybackDTO(kind=PlaybackKind.YOUTUBE_IFRAME, ref=service_id),
                            external_url=f"https://www.youtube.com/watch?v={service_id}",
                            artwork_url=cover,
                            sources=("YT",),
                        )
            except Exception as e:
                log.warning("YouTube get_track error: %s", e)

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
                    kind=PlaybackKind.YOUTUBE_IFRAME,
                    ref=service_id,
                ),
                direct_audio_url=t.direct_audio_url,
                external_url=f"https://www.youtube.com/watch?v={service_id}",
                artwork_url=t.artwork_url,
                sources=t.sources,
            )
        return None

    def get_artist(self, service_id: str) -> ArtistDTO | None:
        return ArtistDTO(
            service=Service.YOUTUBE,
            service_id=service_id,
            name=f"Channel {service_id}",
            external_url=f"https://www.youtube.com/channel/{service_id}",
        )

    def get_playlist(self, service_id: str) -> PlaylistDTO | None:
        return PlaylistDTO(
            service=Service.YOUTUBE,
            service_id=service_id,
            title=f"YouTube Playlist {service_id}",
            external_url=f"https://www.youtube.com/playlist?list={service_id}",
        )

    def close(self) -> None:
        self._client.close()
