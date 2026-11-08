from __future__ import annotations

import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.deps import get_current_active_user
from app.api.uploads import _upload_to_user_file
from app.config import settings
from app.database import get_db
from app.models.upload import UserUpload
from app.models.user import User
from app.schemas.upload import (
    AudioEffectsRequest,
    AudioProcessRequest,
    AudioTrimRequest,
    UserFileRead,
)
from services.audio.editor import AudioEditor, AudioEffectsConfig

router = APIRouter(prefix="/api/editor", tags=["editor"])


@router.post("/trim", response_model=UserFileRead)
async def trim_audio(
    payload: AudioTrimRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> UserFileRead:
    assert current_user.id is not None
    stmt = select(UserUpload).where(UserUpload.id == payload.upload_id, UserUpload.user_id == current_user.id)
    res = await db.exec(stmt)
    upload = res.first()
    if not upload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found")

    input_path = Path(settings.UPLOAD_DIR) / upload.filename
    if not input_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio file on disk not found")

    ext = input_path.suffix.lower()
    upload_dir = Path(settings.UPLOAD_DIR)

    if payload.save_as_new:
        out_filename = f"{current_user.id}_trimmed_{uuid.uuid4().hex[:10]}{ext}"
        out_path = upload_dir / out_filename
    else:
        out_filename = upload.filename
        out_path = input_path

    try:
        meta = AudioEditor.process(
            input_path=input_path,
            output_path=out_path,
            start_sec=payload.start_sec,
            end_sec=payload.end_sec,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Audio trim failed: {str(e)}")

    summary = f"Обрезан: с {payload.start_sec}с" + (f" по {payload.end_sec}с" if payload.end_sec else "")
    title = payload.new_name or (f"{upload.title} (обрезка)" if payload.save_as_new else upload.title)

    if payload.save_as_new:
        new_upload = UserUpload(
            user_id=current_user.id,
            filename=out_filename,
            original_name=f"trimmed_{upload.original_name}",
            title=title,
            artist=upload.artist,
            file_type=meta.file_type,
            file_size_bytes=meta.file_size_bytes,
            duration_seconds=int(round(meta.duration_seconds)),
            is_edited=True,
            parent_id=upload.id,
            edit_summary=summary,
        )
        db.add(new_upload)
        await db.commit()
        await db.refresh(new_upload)
        return _upload_to_user_file(new_upload)
    else:
        upload.file_size_bytes = meta.file_size_bytes
        upload.duration_seconds = int(round(meta.duration_seconds))
        upload.is_edited = True
        upload.edit_summary = summary
        db.add(upload)
        await db.commit()
        await db.refresh(upload)
        return _upload_to_user_file(upload)


@router.post("/effects", response_model=UserFileRead)
async def apply_audio_effects(
    payload: AudioEffectsRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> UserFileRead:
    assert current_user.id is not None
    stmt = select(UserUpload).where(UserUpload.id == payload.upload_id, UserUpload.user_id == current_user.id)
    res = await db.exec(stmt)
    upload = res.first()
    if not upload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found")

    input_path = Path(settings.UPLOAD_DIR) / upload.filename
    if not input_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio file on disk not found")

    ext = input_path.suffix.lower()
    upload_dir = Path(settings.UPLOAD_DIR)

    if payload.save_as_new:
        out_filename = f"{current_user.id}_fx_{uuid.uuid4().hex[:10]}{ext}"
        out_path = upload_dir / out_filename
    else:
        out_filename = upload.filename
        out_path = input_path

    fx_config = AudioEffectsConfig(
        fade_in_sec=payload.fade_in_sec,
        fade_out_sec=payload.fade_out_sec,
        volume_gain_db=payload.volume_gain_db,
        bass_boost_db=payload.bass_boost_db,
        speed_factor=payload.speed_factor,
        normalize=payload.normalize,
        reverse=payload.reverse,
        echo_delay_sec=payload.echo_delay_sec,
        echo_decay=payload.echo_decay,
    )

    try:
        meta = AudioEditor.process(
            input_path=input_path,
            output_path=out_path,
            effects=fx_config,
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Audio effects failed: {str(e)}")

    effects_applied = []
    if payload.bass_boost_db:
        effects_applied.append(f"Bass +{payload.bass_boost_db}dB")
    if payload.volume_gain_db:
        effects_applied.append(f"Gain {payload.volume_gain_db}dB")
    if payload.speed_factor:
        effects_applied.append(f"Speed {payload.speed_factor}x")
    if payload.normalize:
        effects_applied.append("Нормализация")
    if payload.reverse:
        effects_applied.append("Реверс")
    if payload.echo_delay_sec:
        effects_applied.append("Эхо")
    if payload.fade_in_sec:
        effects_applied.append(f"Fade-in {payload.fade_in_sec}s")
    if payload.fade_out_sec:
        effects_applied.append(f"Fade-out {payload.fade_out_sec}s")

    summary = ", ".join(effects_applied) or "Применены эффекты"
    title = payload.new_name or (f"{upload.title} (обработанный)" if payload.save_as_new else upload.title)

    if payload.save_as_new:
        new_upload = UserUpload(
            user_id=current_user.id,
            filename=out_filename,
            original_name=f"fx_{upload.original_name}",
            title=title,
            artist=upload.artist,
            file_type=meta.file_type,
            file_size_bytes=meta.file_size_bytes,
            duration_seconds=int(round(meta.duration_seconds)),
            is_edited=True,
            parent_id=upload.id,
            edit_summary=summary,
        )
        db.add(new_upload)
        await db.commit()
        await db.refresh(new_upload)
        return _upload_to_user_file(new_upload)
    else:
        upload.file_size_bytes = meta.file_size_bytes
        upload.duration_seconds = int(round(meta.duration_seconds)),
        upload.is_edited = True
        upload.edit_summary = summary
        db.add(upload)
        await db.commit()
        await db.refresh(upload)
        return _upload_to_user_file(upload)


@router.post("/process", response_model=UserFileRead)
async def process_audio_pipeline(
    payload: AudioProcessRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> UserFileRead:
    assert current_user.id is not None
    stmt = select(UserUpload).where(UserUpload.id == payload.upload_id, UserUpload.user_id == current_user.id)
    res = await db.exec(stmt)
    upload = res.first()
    if not upload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found")

    input_path = Path(settings.UPLOAD_DIR) / upload.filename
    if not input_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio file on disk not found")

    target_format = (payload.output_format or upload.file_type or "WAV").upper()
    ext = f".{target_format.lower()}"
    upload_dir = Path(settings.UPLOAD_DIR)

    if payload.save_as_new:
        out_filename = f"{current_user.id}_proc_{uuid.uuid4().hex[:10]}{ext}"
        out_path = upload_dir / out_filename
    else:
        out_filename = upload.filename
        out_path = input_path

    fx_config = AudioEffectsConfig(
        fade_in_sec=payload.fade_in_sec,
        fade_out_sec=payload.fade_out_sec,
        volume_gain_db=payload.volume_gain_db,
        bass_boost_db=payload.bass_boost_db,
        speed_factor=payload.speed_factor,
        normalize=payload.normalize,
        reverse=payload.reverse,
        echo_delay_sec=payload.echo_delay_sec,
        echo_decay=payload.echo_decay,
    )

    try:
        meta = AudioEditor.process(
            input_path=input_path,
            output_path=out_path,
            start_sec=payload.start_sec,
            end_sec=payload.end_sec,
            effects=fx_config,
            format_type=target_format,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Audio pipeline failed: {str(e)}")

    summary_parts = []
    if payload.start_sec is not None or payload.end_sec is not None:
        summary_parts.append(f"Обрезан [{payload.start_sec or 0}с-{payload.end_sec or 'end'}с]")
    if payload.bass_boost_db:
        summary_parts.append(f"Bass +{payload.bass_boost_db}dB")
    if payload.speed_factor:
        summary_parts.append(f"Speed {payload.speed_factor}x")
    if payload.normalize:
        summary_parts.append("Нормализация")

    summary = ", ".join(summary_parts) or "Полная обработка"
    title = payload.new_name or (f"{upload.title} (мастеринг)" if payload.save_as_new else upload.title)

    if payload.save_as_new:
        new_upload = UserUpload(
            user_id=current_user.id,
            filename=out_filename,
            original_name=f"processed_{upload.original_name}",
            title=title,
            artist=upload.artist,
            file_type=meta.file_type,
            file_size_bytes=meta.file_size_bytes,
            duration_seconds=int(round(meta.duration_seconds)),
            is_edited=True,
            parent_id=upload.id,
            edit_summary=summary,
        )
        db.add(new_upload)
        await db.commit()
        await db.refresh(new_upload)
        return _upload_to_user_file(new_upload)
    else:
        upload.file_size_bytes = meta.file_size_bytes
        upload.duration_seconds = int(round(meta.duration_seconds))
        upload.is_edited = True
        upload.edit_summary = summary
        db.add(upload)
        await db.commit()
        await db.refresh(upload)
        return _upload_to_user_file(upload)
