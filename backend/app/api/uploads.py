from __future__ import annotations

import logging
import mimetypes
import os
import uuid
from pathlib import Path
from typing import Annotated, Any

from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse, Response
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.deps import (
    get_current_active_user,
    get_current_user,
    get_optional_current_user,
)
from app.config import settings
from app.core.audio_tags import extract_audio_metadata
from app.core.security import decode_token
from app.core.streaming import (
    create_stream_signature,
    range_stream_response,
    verify_stream_signature,
)
from app.database import get_db
from app.models.upload import UserUpload
from app.models.user import User
from app.schemas.upload import CoverUpdateRequest, TrackEditRequest, UserFileRead

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/uploads", tags=["uploads"])

ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac"}
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def _get_covers_dir() -> Path:
    covers_dir = settings.upload_dir_path / "covers"
    covers_dir.mkdir(parents=True, exist_ok=True)
    return covers_dir


def _upload_to_user_file_read(u: UserUpload) -> UserFileRead:
    assert u.id is not None
    size_mb = round(u.file_size_bytes / (1024 * 1024), 1)
    sig = create_stream_signature(u.id, u.user_id)
    audio_url = f"/api/uploads/{u.id}/stream?sig={sig}"

    if u.cover_template:
        cover_val: str | None = u.cover_template
    elif u.cover_file:
        cover_val = f"/api/uploads/{u.id}/cover"
    else:
        cover_val = None

    return UserFileRead(
        id=u.id,
        name=u.title,
        artist=u.artist,
        type=u.file_type.upper(),
        duration=u.duration_seconds,
        size=size_mb,
        audio_url=audio_url,
        cover_url=cover_val,
        created_at=u.created_at,
        cover=cover_val,
        audioUrl=audio_url,
        is_edited=u.is_edited,
        isEdited=u.is_edited,
    )


@router.get("", response_model=list[UserFileRead])
async def list_uploads(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> list[UserFileRead]:
    """List uploaded audio files for the current user, newest first."""
    assert current_user.id is not None
    stmt = (
        select(UserUpload)
        .where(UserUpload.user_id == current_user.id)
        .order_by(UserUpload.created_at.desc())  # type: ignore[attr-defined]
    )
    res = await db.exec(stmt)
    uploads = res.all()
    return [_upload_to_user_file_read(u) for u in uploads]


@router.post("", response_model=UserFileRead, status_code=status.HTTP_201_CREATED)
async def upload_audio_file(
    request: Request,
    current_user: Annotated[User, Depends(get_current_active_user)],
    file: UploadFile = File(...),
    title: str | None = Form(None),
    artist: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
) -> UserFileRead:
    """Upload a new audio file (MP3, WAV, FLAC, OGG, M4A, AAC; max 50 MB) with optional metadata and cover."""
    assert current_user.id is not None

    orig_name = file.filename or ""
    ext = Path(orig_name).suffix.lower()

    if ext not in ALLOWED_AUDIO_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Такой формат не поддерживается — нужен MP3, WAV, FLAC, OGG, M4A или AAC",
        )

    # Read contents and check 50MB limit
    contents = await file.read()
    if len(contents) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Файл больше 50 МБ",
        )

    upload_dir = settings.upload_dir_path
    upload_dir.mkdir(parents=True, exist_ok=True)

    unique_filename = f"{current_user.id}_{uuid.uuid4().hex[:12]}{ext}"
    dest_path = upload_dir / unique_filename

    with open(dest_path, "wb") as f:
        f.write(contents)

    # Extract metadata via Mutagen
    meta = extract_audio_metadata(dest_path)
    duration_sec = meta.duration_seconds
    detected_format = ext.lstrip(".").upper()

    final_title = (
        title.strip()
        if title and title.strip()
        else (meta.title or Path(orig_name).stem)
    )
    final_artist = (
        artist.strip()
        if artist and artist.strip()
        else (meta.artist or "Моя музыка")
    )

    # Cover resolution: form upload / form template / embedded tag
    form = await request.form()
    cover_item: Any = form.get("cover")
    cover_file_name: str | None = None
    cover_template_str: str | None = None

    if hasattr(cover_item, "filename") and getattr(cover_item, "filename", None):
        img_filename = str(cover_item.filename)
        img_ext = Path(img_filename).suffix.lower() or ".jpg"
        if img_ext in ALLOWED_IMAGE_EXTENSIONS:
            cover_file_name = f"{current_user.id}_{uuid.uuid4().hex[:12]}{img_ext}"
            img_dest = _get_covers_dir() / cover_file_name
            img_bytes = await cover_item.read()
            with open(img_dest, "wb") as f_img:
                f_img.write(img_bytes)
    elif isinstance(cover_item, str) and cover_item.strip():
        cover_val = cover_item.strip()
        if cover_val.startswith("template:"):
            cover_template_str = cover_val
    elif meta.cover_bytes:
        ext_map = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}
        c_ext = ext_map.get(meta.cover_mime or "", ".jpg")
        cover_file_name = f"{current_user.id}_{uuid.uuid4().hex[:12]}{c_ext}"
        img_dest = _get_covers_dir() / cover_file_name
        with open(img_dest, "wb") as f_img:
            f_img.write(meta.cover_bytes)

    user_upload = UserUpload(
        user_id=current_user.id,
        filename=unique_filename,
        original_name=orig_name,
        title=final_title,
        artist=final_artist,
        file_type=detected_format,
        file_size_bytes=len(contents),
        duration_seconds=duration_sec,
        cover_file=cover_file_name,
        cover_template=cover_template_str,
        is_edited=False,
    )
    db.add(user_upload)
    await db.commit()
    await db.refresh(user_upload)

    return _upload_to_user_file_read(user_upload)


@router.get("/{upload_id}", response_model=UserFileRead)
async def get_upload(
    upload_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> UserFileRead:
    """Get metadata for a specific uploaded track."""
    assert current_user.id is not None
    stmt = select(UserUpload).where(
        UserUpload.id == upload_id,
        UserUpload.user_id == current_user.id,
    )
    res = await db.exec(stmt)
    upload = res.first()
    if not upload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Аудиозапись не найдена",
        )
    return _upload_to_user_file_read(upload)


@router.patch("/{upload_id}", response_model=UserFileRead)
async def edit_upload(
    upload_id: int,
    req: TrackEditRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> UserFileRead:
    """Edit title and artist of an uploaded track."""
    assert current_user.id is not None
    stmt = select(UserUpload).where(
        UserUpload.id == upload_id,
        UserUpload.user_id == current_user.id,
    )
    res = await db.exec(stmt)
    upload = res.first()
    if not upload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Аудиозапись не найдена",
        )

    new_title = req.title if req.title is not None else req.name
    if new_title is not None and new_title.strip():
        upload.title = new_title.strip()
        upload.is_edited = True

    if req.artist is not None:
        upload.artist = req.artist.strip() or "Моя музыка"
        upload.is_edited = True

    db.add(upload)
    await db.commit()
    await db.refresh(upload)

    return _upload_to_user_file_read(upload)


@router.put("/{upload_id}/cover", response_model=UserFileRead)
async def update_upload_cover(
    upload_id: int,
    request: Request,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> UserFileRead:
    """Set or replace the cover image or cover template for an uploaded track."""
    assert current_user.id is not None
    stmt = select(UserUpload).where(
        UserUpload.id == upload_id,
        UserUpload.user_id == current_user.id,
    )
    res = await db.exec(stmt)
    upload = res.first()
    if not upload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Аудиозапись не найдена",
        )

    content_type = request.headers.get("content-type", "")

    # Handle JSON payload {"cover": "template:3"}
    if content_type.startswith("application/json"):
        try:
            body = await request.json()
            cover_val = str(body.get("cover", "")).strip()
        except Exception:
            cover_val = ""

        if cover_val.startswith("template:"):
            # Remove previous file cover if existed
            if upload.cover_file:
                old_file = _get_covers_dir() / upload.cover_file
                if old_file.exists():
                    try:
                        os.remove(old_file)
                    except OSError:
                        pass
                upload.cover_file = None

            upload.cover_template = cover_val
            upload.is_edited = True
            db.add(upload)
            await db.commit()
            await db.refresh(upload)
            return _upload_to_user_file_read(upload)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ожидается шаблонная обложка в формате 'template:<номер>'",
            )

    # Handle multipart/form-data
    form = await request.form()
    file_item: Any = form.get("file")
    cover_item: Any = form.get("cover")

    if hasattr(file_item, "filename") and getattr(file_item, "filename", None):
        img_filename = str(file_item.filename)
        img_ext = Path(img_filename).suffix.lower()
        if img_ext not in ALLOWED_IMAGE_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Неподдерживаемый формат изображения {img_ext}. Допустимы: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}",
            )

        # Remove previous file cover if existed
        if upload.cover_file:
            old_file = _get_covers_dir() / upload.cover_file
            if old_file.exists():
                try:
                    os.remove(old_file)
                except OSError:
                    pass

        new_cover_name = f"{current_user.id}_{uuid.uuid4().hex[:12]}{img_ext}"
        img_dest = _get_covers_dir() / new_cover_name
        img_bytes = await file_item.read()
        with open(img_dest, "wb") as f_img:
            f_img.write(img_bytes)

        upload.cover_file = new_cover_name
        upload.cover_template = None
        upload.is_edited = True
        db.add(upload)
        await db.commit()
        await db.refresh(upload)
        return _upload_to_user_file_read(upload)

    elif isinstance(cover_item, str) and cover_item.strip().startswith("template:"):
        # Remove previous file cover if existed
        if upload.cover_file:
            old_file = _get_covers_dir() / upload.cover_file
            if old_file.exists():
                try:
                    os.remove(old_file)
                except OSError:
                    pass
            upload.cover_file = None

        upload.cover_template = cover_item.strip()
        upload.is_edited = True
        db.add(upload)
        await db.commit()
        await db.refresh(upload)
        return _upload_to_user_file_read(upload)

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Необходимо передать файл изображения в поле 'file' или шаблон в поле 'cover'",
    )


@router.delete("/{upload_id}/cover", response_model=UserFileRead)
async def delete_upload_cover(
    upload_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> UserFileRead:
    """Remove cover image or template from an uploaded track."""
    assert current_user.id is not None
    stmt = select(UserUpload).where(
        UserUpload.id == upload_id,
        UserUpload.user_id == current_user.id,
    )
    res = await db.exec(stmt)
    upload = res.first()
    if not upload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Аудиозапись не найдена",
        )

    if upload.cover_file:
        old_file = _get_covers_dir() / upload.cover_file
        if old_file.exists():
            try:
                os.remove(old_file)
            except OSError:
                pass
        upload.cover_file = None

    upload.cover_template = None
    upload.is_edited = True
    db.add(upload)
    await db.commit()
    await db.refresh(upload)

    return _upload_to_user_file_read(upload)


@router.delete("/{upload_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_upload(
    upload_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Delete an uploaded track and its files from disk and database."""
    assert current_user.id is not None
    stmt = select(UserUpload).where(
        UserUpload.id == upload_id,
        UserUpload.user_id == current_user.id,
    )
    res = await db.exec(stmt)
    upload = res.first()
    if not upload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Аудиозапись не найдена",
        )

    # Delete audio file
    audio_path = settings.upload_dir_path / upload.filename
    if audio_path.exists():
        try:
            os.remove(audio_path)
        except OSError:
            pass

    # Delete cover file
    if upload.cover_file:
        cover_path = _get_covers_dir() / upload.cover_file
        if cover_path.exists():
            try:
                os.remove(cover_path)
            except OSError:
                pass

    await db.delete(upload)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{upload_id}/stream")
async def stream_upload_audio(
    upload_id: int,
    request: Request,
    sig: str | None = Query(None, description="HMAC stream signature for unauthenticated HTML5 audio playback"),
    token: str | None = Query(None, description="Optional JWT access token via query string"),
    access_token_cookie: str | None = Cookie(None, alias="access_token"),
    current_user: Annotated[User | None, Depends(get_optional_current_user)] = None,
    db: AsyncSession = Depends(get_db),
):
    """Streams audio file with HTTP Range (206 Partial Content) support.

    Accepts:
    1. Signed URL (?sig=...)
    2. Query string access token (?token=...)
    3. Authorization: Bearer <token>
    4. Cookie (access_token=...)
    """
    stmt = select(UserUpload).where(UserUpload.id == upload_id)
    res = await db.exec(stmt)
    upload = res.first()
    if not upload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Аудиозапись не найдена",
        )

    # Authorization verification
    authorized = False

    # 1. Signature check
    if sig and verify_stream_signature(upload.id or 0, upload.user_id, sig):
        authorized = True

    # 2. Bearer header check
    if not authorized and current_user and current_user.id == upload.user_id:
        authorized = True

    # 3. Query token check
    if not authorized and token:
        try:
            payload = decode_token(token)
            if payload.get("type") == "access" and int(payload.get("sub", 0)) == upload.user_id:
                authorized = True
        except Exception:
            pass

    # 4. Cookie check
    if not authorized and access_token_cookie:
        try:
            payload = decode_token(access_token_cookie)
            if payload.get("type") == "access" and int(payload.get("sub", 0)) == upload.user_id:
                authorized = True
        except Exception:
            pass

    if not authorized:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Необходима авторизация или действительная подпись для воспроизведения аудио",
        )

    audio_path = settings.upload_dir_path / upload.filename
    if not audio_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Файл на диске не найден",
        )

    return range_stream_response(
        audio_path,
        request,
        filename=f"{upload.title}.{upload.file_type.lower()}",
    )


@router.get("/{upload_id}/cover")
async def get_upload_cover(
    upload_id: int,
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    """Serve the cover image for an uploaded track."""
    stmt = select(UserUpload).where(UserUpload.id == upload_id)
    res = await db.exec(stmt)
    upload = res.first()
    if not upload or not upload.cover_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Обложка не найдена",
        )

    cover_path = _get_covers_dir() / upload.cover_file
    if not cover_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Файл обложки на диске не найден",
        )

    content_type, _ = mimetypes.guess_type(str(cover_path))
    return FileResponse(cover_path, media_type=content_type or "image/jpeg")
