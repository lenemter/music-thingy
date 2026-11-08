from __future__ import annotations

import logging
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse, StreamingResponse

from app.api.deps import get_optional_current_user
from app.config import settings
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
from services.music.dto import CODE_TO_SERVICE_MAP, SearchType, Service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/music", tags=["music"])


@router.get("/services", response_model=list[ServiceStatusRead])
async def list_music_services() -> list[ServiceStatusRead]:
    """Returns the list of music source services and their online status."""
    statuses = aggregator.get_services_status()
    return [ServiceStatusRead(**s) for s in statuses]


@router.get("/search", response_model=MusicSearchResponse)
async def search_music(
    q: str = Query(..., min_length=1, description="Search query string"),
    services: str | None = Query(None, description="Comma-separated services: yandex,spotify,soundcloud,youtube"),
    types: str | None = Query("track,album", description="Comma-separated types: track,album,artist,playlist"),
    limit: int = Query(
        settings.DEFAULT_SEARCH_LIMIT,
        ge=1,
        le=settings.MAX_SEARCH_LIMIT,
        description="Results limit per service",
    ),
    current_user: Annotated[User | None, Depends(get_optional_current_user)] = None,
) -> MusicSearchResponse:
    """Search for tracks, albums, artists, and playlists across enabled music services."""
    target_services: list[str] = []
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


@router.get("/tracks/{service}/{service_id}", response_model=TrackRead)
async def get_track(
    service: str,
    service_id: str,
    current_user: Annotated[User | None, Depends(get_optional_current_user)] = None,
) -> TrackRead:
    """Retrieve full track metadata and playback parameters by service and service ID."""
    track_dto = await aggregator.get_track(service, service_id)
    if not track_dto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Track '{service_id}' on service '{service}' not found",
        )

    return TrackRead(**track_dto.to_frontend_dict())


@router.get("/playback/{service}/{service_id}", response_model=PlaybackInfo)
async def get_playback_info(
    service: str,
    service_id: str,
    current_user: Annotated[User | None, Depends(get_optional_current_user)] = None,
) -> PlaybackInfo:
    """Retrieve playback parameters (iframe ref, SDK ref, direct audio url) for a track."""
    track_dto = await aggregator.get_track(service, service_id)
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
):
    """Stream audio content for a track with HTTP Range header support or redirect to direct audio URL."""
    track_dto = await aggregator.get_track(service, service_id)
    if not track_dto or not track_dto.direct_audio_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audio stream not available for track '{service_id}' on service '{service}'",
        )

    audio_url = str(track_dto.direct_audio_url)

    if redirect:
        return RedirectResponse(url=audio_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)

    headers = {}
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
async def get_playlist(service: str, service_id: str) -> PlaylistRead:
    """Retrieve playlist details and tracklist by service and playlist ID."""
    pl_dto = await aggregator.get_playlist(service, service_id)
    if not pl_dto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Playlist '{service_id}' on service '{service}' not found",
        )
    return PlaylistRead(**pl_dto.to_frontend_dict())
