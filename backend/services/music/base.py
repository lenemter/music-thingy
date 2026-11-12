from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar, Self
from .dto import (
    AlbumDTO,
    ArtistDTO,
    ErrorKind,
    PlaylistDTO,
    SearchResultDTO,
    SearchType,
    Service,
    TrackDTO,
)


class AdapterError(Exception):
    def __init__(self, kind: ErrorKind, message: str, status_code: int | None = None):
        super().__init__(message)
        self.kind, self.status_code = kind, status_code


class BaseMusicAdapter(ABC):
    service: ClassVar[Service]
    official: ClassVar[bool] = True

    @abstractmethod
    def search(
        self,
        query: str,
        types: frozenset[SearchType] = frozenset({SearchType.TRACK}),
        limit: int = 10,
    ) -> SearchResultDTO: ...

    @abstractmethod
    def get_track(self, service_id: str) -> TrackDTO | None: ...

    @abstractmethod
    def get_playlist(self, service_id: str) -> PlaylistDTO | None: ...

    @abstractmethod
    def get_artist(self, service_id: str) -> ArtistDTO | None: ...

    def get_album(self, service_id: str) -> AlbumDTO | None:
        return None

    @classmethod
    def create_from_credentials(
        cls,
        token: str | None = None,
        extra_data: str | None = None,
    ) -> BaseMusicAdapter | None:
        """Create an adapter instance configured with user credentials."""
        return None

    def get_user_playlists(
        self,
        account_id: str | None = None,
        limit: int = 50,
    ) -> list[PlaylistDTO]:
        """Fetch user's playlists for this service."""
        return []

    def get_user_favorites(
        self,
        account_id: str | None = None,
        limit: int = 50,
    ) -> list[TrackDTO]:
        """Fetch user's liked/favorite tracks for this service."""
        return []

    def set_track_like(
        self,
        service_id: str,
        liked: bool,
    ) -> bool:
        """Like or unlike a track in this service. Returns True if succeeded."""
        return False

    def close(self) -> None: ...
    def __enter__(self) -> Self: return self
    def __exit__(self, *exc) -> None: self.close()
