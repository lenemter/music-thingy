from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class UserFileRead(BaseModel):
    id: int
    name: str
    type: str
    duration: int
    size: int  # in megabytes, matching frontend type (e.g. 31, 9)
    size_bytes: int
    audio_url: str
    is_edited: bool = False
    parent_id: int | None = None
    edit_summary: str | None = None
    created_at: datetime


class AudioTrimRequest(BaseModel):
    upload_id: int
    start_sec: float = Field(default=0.0, ge=0.0)
    end_sec: float | None = Field(default=None, gt=0.0)
    save_as_new: bool = True
    new_name: str | None = None


class AudioEffectsRequest(BaseModel):
    upload_id: int
    fade_in_sec: float | None = Field(default=None, ge=0.0)
    fade_out_sec: float | None = Field(default=None, ge=0.0)
    volume_gain_db: float | None = Field(default=None, ge=-30.0, le=30.0)
    bass_boost_db: float | None = Field(default=None, ge=-12.0, le=24.0)
    speed_factor: float | None = Field(default=None, ge=0.25, le=4.0)
    normalize: bool = False
    reverse: bool = False
    echo_delay_sec: float | None = Field(default=None, ge=0.0, le=2.0)
    echo_decay: float = Field(default=0.4, ge=0.0, le=1.0)
    save_as_new: bool = True
    new_name: str | None = None


class AudioProcessRequest(BaseModel):
    upload_id: int
    start_sec: float | None = Field(default=None, ge=0.0)
    end_sec: float | None = Field(default=None, gt=0.0)
    fade_in_sec: float | None = Field(default=None, ge=0.0)
    fade_out_sec: float | None = Field(default=None, ge=0.0)
    volume_gain_db: float | None = Field(default=None, ge=-30.0, le=30.0)
    bass_boost_db: float | None = Field(default=None, ge=-12.0, le=24.0)
    speed_factor: float | None = Field(default=None, ge=0.25, le=4.0)
    normalize: bool = False
    reverse: bool = False
    echo_delay_sec: float | None = Field(default=None, ge=0.0, le=2.0)
    echo_decay: float = Field(default=0.4, ge=0.0, le=1.0)
    output_format: str | None = None  # WAV, MP3, FLAC, OGG
    save_as_new: bool = True
    new_name: str | None = None
