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
    "AlbumRead",
    "ArtistRead",
    "ConnectServiceRequest",
    "CoverUpdateRequest",
    "LikeRequest",
    "LikeResponse",
    "LoginRequest",
    "MusicSearchResponse",
    "PlaybackInfo",
    "PlaylistRead",
    "RefreshTokenRequest",
    "ServiceConnectionStatus",
    "ServiceErrorRead",
    "ServiceStatusRead",
    "ToggleServiceRequest",
    "Token",
    "TrackEditRequest",
    "TrackRead",
    "UserBase",
    "UserCreate",
    "UserFileRead",
    "UserRead",
    "YouTubeDeviceCodeResponse",
    "YouTubePollTokenRequest",
]
