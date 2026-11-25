from __future__ import annotations

import contextlib
import logging
import re
import time
from typing import Any

import httpx

from .dto import PlaybackDTO, PlaybackKind, PlaylistDTO, Service, TrackDTO

log = logging.getLogger(__name__)

_API = "https://www.googleapis.com/youtube/v3"
_TOKEN_URL = "https://oauth2.googleapis.com/token"
_WEB_URL = "https://music.youtube.com"
_PAGE_SIZE = 50
_token_cache: dict[str, tuple[str, float]] = {}
_DURATION_RE = re.compile(r"^P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?$")


class YouTubeDataApiError(Exception):
    pass


def _parse_iso_duration_ms(value: Any) -> int | None:
    if not isinstance(value, str):
        return None
    m = _DURATION_RE.match(value)
    if not m:
        return None
    days, hours, minutes, seconds = (int(x) if x else 0 for x in m.groups())
    return ((days * 24 + hours) * 3600 + minutes * 60 + seconds) * 1000


def _best_thumbnail(thumbs: Any) -> str | None:
    if not isinstance(thumbs, dict):
        return None
    for size in ("maxres", "standard", "high", "medium", "default"):
        url = (thumbs.get(size) or {}).get("url")
        if isinstance(url, str) and url.startswith("http"):
            return url
    return None


def _artist_from_channel(title: Any) -> tuple[str, ...]:
    name = str(title or "").removesuffix(" - Topic").strip()
    return (name,) if name else ()


def _video_to_track(video: dict[str, Any]) -> TrackDTO | None:
    vid = video.get("id")
    snippet = video.get("snippet") or {}
    title = snippet.get("title")
    if not isinstance(vid, str) or not title:
        return None
    status = video.get("status") or {}
    is_playable = status.get("embeddable", True) is not False and status.get("privacyStatus") != "private"
    return TrackDTO(
        service=Service.YOUTUBE,
        service_id=vid,
        title=str(title),
        artists=_artist_from_channel(snippet.get("videoOwnerChannelTitle") or snippet.get("channelTitle")),
        is_playable=is_playable,
        duration_ms=_parse_iso_duration_ms((video.get("contentDetails") or {}).get("duration")),
        playback=PlaybackDTO(kind=PlaybackKind.YOUTUBE_IFRAME, ref=vid) if is_playable else None,
        external_url=f"{_WEB_URL}/watch?v={vid}",
        artwork_url=_best_thumbnail(snippet.get("thumbnails")),
    )


def _playlist_to_dto(item: dict[str, Any], tracks: tuple[TrackDTO, ...] | None = None) -> PlaylistDTO | None:
    pid = item.get("id")
    snippet = item.get("snippet") or {}
    title = snippet.get("title")
    if not isinstance(pid, str) or not title:
        return None
    count = (item.get("contentDetails") or {}).get("itemCount")
    return PlaylistDTO(
        service=Service.YOUTUBE,
        service_id=pid,
        title=str(title),
        description=snippet.get("description") or None,
        owner_name=snippet.get("channelTitle") or None,
        tracks_count=count if isinstance(count, int) else (len(tracks) if tracks is not None else None),
        artwork_url=_best_thumbnail(snippet.get("thumbnails")),
        external_url=f"{_WEB_URL}/playlist?list={pid}",
        tracks=tracks,
    )


class YouTubeDataApi:

    def __init__(self, token: dict[str, Any], client_id: str, client_secret: str, timeout: float = 15.0) -> None:
        self._refresh_token = token.get("refresh_token")
        cached = _token_cache.get(self._refresh_token or "")
        self._access_token: str | None = cached[0] if cached else None
        self._expires_at = cached[1] if cached else 0.0
        self._client_id = client_id
        self._client_secret = client_secret
        self._http = httpx.Client(timeout=timeout)

    def _refresh(self) -> str:
        if not self._refresh_token:
            raise YouTubeDataApiError("Нет refresh token — привяжите YouTube заново")
        resp = self._http.post(_TOKEN_URL, data={
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "refresh_token": self._refresh_token,
            "grant_type": "refresh_token",
        })
        if resp.status_code != 200:
            raise YouTubeDataApiError(f"Google не обновил доступ (HTTP {resp.status_code}) — привяжите YouTube заново")
        data = resp.json()
        self._access_token = data["access_token"]
        self._expires_at = time.time() + int(data.get("expires_in", 3600)) - 60
        _token_cache[self._refresh_token] = (self._access_token, self._expires_at)
        return self._access_token

    def _token(self) -> str:
        if not self._access_token or time.time() >= self._expires_at:
            return self._refresh()
        return self._access_token

    def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        for attempt in range(2):
            resp = self._http.get(f"{_API}/{path}", params=params, headers={"Authorization": f"Bearer {self._token()}"})
            if resp.status_code == 401 and attempt == 0:
                self._refresh()
                continue
            if resp.status_code != 200:
                reason = ""
                with contextlib.suppress(ValueError, KeyError, IndexError, TypeError):
                    reason = resp.json()["error"]["errors"][0]["reason"]
                raise YouTubeDataApiError(f"YouTube Data API: HTTP {resp.status_code} {reason}".strip())
            return resp.json()
        raise YouTubeDataApiError("YouTube Data API: доступ не обновился")

    def _paginate(self, path: str, params: dict[str, Any], limit: int | None) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        page_token: str | None = None
        while limit is None or len(items) < limit:
            page = self._get(path, {**params, "maxResults": _PAGE_SIZE, **({"pageToken": page_token} if page_token else {})})
            items.extend(i for i in page.get("items") or [] if isinstance(i, dict))
            page_token = page.get("nextPageToken")
            if not page_token:
                break
        return items if limit is None else items[:limit]

    def _videos(self, video_ids: list[str]) -> list[dict[str, Any]]:
        by_id: dict[str, dict[str, Any]] = {}
        for start in range(0, len(video_ids), _PAGE_SIZE):
            chunk = video_ids[start:start + _PAGE_SIZE]
            page = self._get("videos", {"part": "snippet,contentDetails,status", "id": ",".join(chunk), "maxResults": _PAGE_SIZE})
            for video in page.get("items") or []:
                if isinstance(video, dict) and isinstance(video.get("id"), str):
                    by_id[video["id"]] = video
        return [by_id[v] for v in video_ids if v in by_id]

    def user_playlists(self, limit: int | None = None) -> list[PlaylistDTO]:
        try:
            items = self._paginate("playlists", {"part": "snippet,contentDetails", "mine": "true"}, limit)
        except YouTubeDataApiError as e:
            if "channelNotFound" in str(e) or "404" in str(e):
                log.warning("YouTube account has no channel — no playlists to show")
                return []
            raise
        return [p for i in items if (p := _playlist_to_dto(i)) is not None]

    def liked_tracks(self, limit: int | None = 50) -> list[TrackDTO]:
        items = self._paginate("videos", {"part": "snippet,contentDetails,status", "myRating": "like"}, limit)
        return [t for v in items if (t := _video_to_track(v)) is not None]

    def playlist(self, playlist_id: str, limit: int | None = 200) -> PlaylistDTO | None:
        meta = self._get("playlists", {"part": "snippet,contentDetails", "id": playlist_id, "maxResults": 1})
        meta_items = [i for i in meta.get("items") or [] if isinstance(i, dict)]
        if not meta_items:
            return None
        entries = self._paginate("playlistItems", {"part": "contentDetails", "playlistId": playlist_id}, limit)
        video_ids = [vid for e in entries if isinstance(vid := (e.get("contentDetails") or {}).get("videoId"), str)]
        tracks = tuple(t for v in self._videos(video_ids) if (t := _video_to_track(v)) is not None)
        return _playlist_to_dto(meta_items[0], tracks=tracks)
