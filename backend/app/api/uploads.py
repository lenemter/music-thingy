from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.deps import get_current_active_user, get_optional_current_user
from app.config import settings
from app.core.streaming import range_stream_response
from app.database import get_db
from app.models.upload import UserUpload
from app.models.user import User
from app.schemas.upload import UserFileRead
from services.audio.editor import AudioEditor

router = APIRouter(prefix="/api/uploads", tags=["uploads"])


def _upload_to_user_file(u: UserUpload) -> UserFileRead:
    size_mb = max(1, round(u.file_size_bytes / (1024 * 1024)))
    assert u.id is not None
    return UserFileRead(
        id=u.id,
        name=u.title or u.original_name,
        type=u.file_type.upper(),
        duration=u.duration_seconds,
        size=size_mb,
        size_bytes=u.file_size_bytes,
        audio_url=f"/api/uploads/{u.id}/stream",
        is_edited=u.is_edited,
        parent_id=u.parent_id,
        edit_summary=u.edit_summary,
        created_at=u.created_at,
    )


@router.get("", response_model=list[UserFileRead])
@router.get("/", response_model=list[UserFileRead], include_in_schema=False)
async def list_uploads(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> list[UserFileRead]:
    assert current_user.id is not None
    stmt = (
        select(UserUpload)
        .where(UserUpload.user_id == current_user.id)
        .order_by(UserUpload.created_at.desc())
    )
    res = await db.exec(stmt)
    uploads = res.all()
    return [_upload_to_user_file(u) for u in uploads]


@router.post("", response_model=UserFileRead, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=UserFileRead, status_code=status.HTTP_201_CREATED, include_in_schema=False)
async def upload_audio_file(
    current_user: Annotated[User, Depends(get_current_active_user)],
    file: UploadFile = File(...),
    title: str | None = Form(None),
    artist: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
) -> UserFileRead:
    assert current_user.id is not None
    orig_name = file.filename or "track.wav"
    ext = Path(orig_name).suffix.lower()

    allowed_exts = {".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac"}
    if ext not in allowed_exts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported audio format {ext}. Allowed: {', '.join(allowed_exts)}",
        )

    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    unique_filename = f"{current_user.id}_{uuid.uuid4().hex[:12]}{ext}"
    dest_path = upload_dir / unique_filename

    # Read and validate size
    contents = await file.read()
    if len(contents) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum size of {settings.MAX_UPLOAD_SIZE_BYTES // (1024*1024)} MB",
        )

    with open(dest_path, "wb") as f:
        f.write(contents)

    # Inspect audio metadata
    try:
        meta = AudioEditor.get_metadata(dest_path)
        duration_sec = int(round(meta.duration_seconds))
        detected_format = meta.file_type or ext.lstrip(".").upper()
        detected_title = meta.title or Path(orig_name).stem
        detected_artist = meta.artist or current_user.display_name or "Пользователь"
    except Exception as e:
        duration_sec = 0
        detected_format = ext.lstrip(".").upper()
        detected_title = Path(orig_name).stem
        detected_artist = current_user.display_name or "Пользователь"

    final_title = title.strip() if title else detected_title
    final_artist = artist.strip() if artist else detected_artist

    user_upload = UserUpload(
        user_id=current_user.id,
        filename=unique_filename,
        original_name=orig_name,
        title=final_title,
        artist=final_artist,
        file_type=detected_format,
        file_size_bytes=len(contents),
        duration_seconds=duration_sec,
        is_edited=False,
    )
    db.add(user_upload)
    await db.commit()
    await db.refresh(user_upload)

    return _upload_to_user_file(user_upload)


@router.get("/{upload_id}", response_model=UserFileRead)
async def get_upload(
    upload_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> UserFileRead:
    assert current_user.id is not None
    stmt = select(UserUpload).where(UserUpload.id == upload_id, UserUpload.user_id == current_user.id)
    res = await db.exec(stmt)
    upload = res.first()
    if not upload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio file not found")
    return _upload_to_user_file(upload)


@router.delete("/{upload_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_upload(
    upload_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> None:
    assert current_user.id is not None
    stmt = select(UserUpload).where(UserUpload.id == upload_id, UserUpload.user_id == current_user.id)
    res = await db.exec(stmt)
    upload = res.first()
    if not upload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio file not found")

    file_path = Path(settings.UPLOAD_DIR) / upload.filename
    if file_path.exists():
        try:
            os.remove(file_path)
        except OSError:
            pass

    await db.delete(upload)
    await db.commit()


@router.get("/{upload_id}/stream")
async def stream_upload_audio(
    upload_id: int,
    request: Request,
    current_user: Annotated[User | None, Depends(get_optional_current_user)] = None,
    db: AsyncSession = Depends(get_db),
):
    """Streams audio file with HTTP 206 Partial Content support for scrubber seeking."""
    stmt = select(UserUpload).where(UserUpload.id == upload_id)
    res = await db.exec(stmt)
    upload = res.first()
    if not upload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio file not found")

    file_path = Path(settings.UPLOAD_DIR) / upload.filename
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio file on disk not found")

    return range_stream_response(file_path, request)
