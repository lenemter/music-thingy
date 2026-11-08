from abc import ABC, abstractmethod
from typing import ClassVar, Self
from .dto import (ArtistDTO, ErrorKind, PlaylistDTO, SearchResultDTO,
                  SearchType, Service, TrackDTO)


class AdapterError(Exception):
    def __init__(self, kind: ErrorKind, message: str, status_code: int | None = None):
        super().__init__(message)
        self.kind, self.status_code = kind, status_code


class BaseMusicAdapter(ABC):
    service: ClassVar[Service]
    official: ClassVar[bool] = True

    @abstractmethod
    def search(self, query: str, types: frozenset[SearchType] = frozenset({SearchType.TRACK}),
               limit: int = 10) -> SearchResultDTO: ...

    @abstractmethod
    def get_track(self, service_id: str) -> TrackDTO | None: ...
    @abstractmethod
    def get_playlist(self, service_id: str) -> PlaylistDTO | None: ...
    @abstractmethod
    def get_artist(self, service_id: str) -> ArtistDTO | None: ...

    def close(self) -> None: ...
    def __enter__(self) -> Self: return self
    def __exit__(self, *exc) -> None: self.close()
