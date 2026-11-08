from app.api.auth import router as auth_router
from app.api.music import router as music_router
from app.api.services import router as services_router

__all__ = ["auth_router", "music_router", "services_router"]
