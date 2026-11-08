from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Compatibility safeguard for psycopg async on Windows
if sys.platform == "win32":
    import asyncio
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        except Exception:
            pass

from app.api.auth import router as auth_router
from app.api.editor import router as editor_router
from app.api.favorites import router as favorites_router
from app.api.history import router as history_router
from app.api.music import router as music_router
from app.api.playlists import router as playlists_router
from app.api.recommendations import router as recommendations_router
from app.api.services import router as services_router
from app.api.uploads import router as uploads_router
from app.config import settings
from app.database import close_db, init_db

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure uploads directory exists
    Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)

    # Initialize database tables on startup
    try:
        await init_db()
        logger.info("Database tables initialized successfully.")
    except Exception as e:
        logger.warning("Could not initialize database on startup: %s", e)
    yield
    await close_db()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Backend API для музыкального агрегатора: мультисервисный поиск (Яндекс Музыка, Spotify, SoundCloud, YouTube), стриминг, плейлисты, избранное, история, рекомендации, загрузка треков и встроенный редактор аудио с эффектами.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if not settings.DEBUG else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all API routers
app.include_router(auth_router)
app.include_router(services_router)
app.include_router(music_router)
app.include_router(playlists_router)
app.include_router(favorites_router)
app.include_router(history_router)
app.include_router(recommendations_router)
app.include_router(uploads_router)
app.include_router(editor_router)


@app.get("/health", tags=["system"])
async def health_check():
    return {
        "status": "ok",
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
    }
