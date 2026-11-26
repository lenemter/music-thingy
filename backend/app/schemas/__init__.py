from app.schemas.auth import LoginRequest, RefreshTokenRequest, Token
from app.schemas.music import (
    AlbumRead,
    ArtistRead,
    LikeRequest,
    LikeResponse,
    MusicSearchResponse,
    PlaybackInfo,
    PlaylistRead,
    ServiceErrorRead,
    TrackRead,
)
from app.schemas.playlist import (
    PlaylistCreateRequest,
    PlaylistUpdateRequest,
    TrackRef,
    UserPlaylistRead,
)
from app.schemas.service import (
    ConnectServiceRequest,
    ServiceConnectionStatus,
    ServiceStatusRead,
    ToggleServiceRequest,
    YouTubeDeviceCodeResponse,
    YouTubePollTokenRequest,
)
from app.schemas.upload import CoverUpdateRequest, TrackEditRequest, UserFileRead
from app.schemas.user import UserBase, UserCreate, UserRead

__all__ = [
    "AlbumRead",
    "ArtistRead",
    "ConnectServiceRequest",
    "CoverUpdateRequest",
    "LikeRequest",
    "LikeResponse",
    "LoginRequest",
    "MusicSearchResponse",
    "PlaybackInfo",
    "PlaylistCreateRequest",
    "PlaylistRead",
    "PlaylistUpdateRequest",
    "RefreshTokenRequest",
    "ServiceConnectionStatus",
    "ServiceErrorRead",
    "ServiceStatusRead",
    "ToggleServiceRequest",
    "Token",
    "TrackEditRequest",
    "TrackRead",
    "TrackRef",
    "UserBase",
    "UserCreate",
    "UserFileRead",
    "UserPlaylistRead",
    "UserRead",
    "YouTubeDeviceCodeResponse",
    "YouTubePollTokenRequest",
]
