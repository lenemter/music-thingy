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
    "LoginRequest",
    "RefreshTokenRequest",
    "Token",
    "UserBase",
    "UserCreate",
    "UserRead",
    "PlaybackInfo",
    "TrackRead",
    "LikeRequest",
    "LikeResponse",
    "AlbumRead",
    "ArtistRead",
    "PlaylistRead",
    "ServiceErrorRead",
    "MusicSearchResponse",
    "ServiceStatusRead",
    "ServiceConnectionStatus",
    "ConnectServiceRequest",
    "ToggleServiceRequest",
    "YouTubeDeviceCodeResponse",
    "YouTubePollTokenRequest",
    "UserFileRead",
    "TrackEditRequest",
    "CoverUpdateRequest",
]
