from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import mutagen
import numpy as np
import soundfile as sf
from scipy import signal

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AudioMetadata:
    duration_seconds: float
    sample_rate: int
    channels: int
    file_type: str
    file_size_bytes: int
    bitrate: int | None = None
    title: str | None = None
    artist: str | None = None


@dataclass
class AudioEffectsConfig:
    fade_in_sec: float | None = None
    fade_out_sec: float | None = None
    volume_gain_db: float | None = None
    bass_boost_db: float | None = None
    speed_factor: float | None = None  # e.g., 0.8 to 2.0
    normalize: bool = False
    reverse: bool = False
    echo_delay_sec: float | None = None
    echo_decay: float = 0.4


class AudioEditor:
    """High performance audio processing engine for music trimming and effects."""

    @staticmethod
    def get_metadata(file_path: str | Path) -> AudioMetadata:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Audio file not found: {path}")

        file_size = path.stat().st_size
        ext = path.suffix.lstrip(".").upper() or "WAV"

        duration = 0.0
        sample_rate = 44100
        channels = 2
        bitrate = None
        title = None
        artist = None

        # 1. Try mutagen for rich tags and accurate container duration
        try:
            m = mutagen.File(str(path))
            if m is not None:
                if hasattr(m.info, "length") and m.info.length:
                    duration = float(m.info.length)
                if hasattr(m.info, "sample_rate") and m.info.sample_rate:
                    sample_rate = int(m.info.sample_rate)
                if hasattr(m.info, "channels") and m.info.channels:
                    channels = int(m.info.channels)
                if hasattr(m.info, "bitrate") and m.info.bitrate:
                    bitrate = int(m.info.bitrate)

                # Extract basic tags if present
                for t_key in ("title", "TIT2"):
                    if t_key in m.tags:
                        val = m.tags[t_key]
                        title = str(val[0]) if isinstance(val, (list, tuple)) else str(val)
                        break
                for a_key in ("artist", "TPE1"):
                    if a_key in m.tags:
                        val = m.tags[a_key]
                        artist = str(val[0]) if isinstance(val, (list, tuple)) else str(val)
                        break
        except Exception as e:
            logger.debug("Mutagen inspection failed for %s: %s", path, e)

        # 2. Fall back to soundfile if duration is not resolved
        if duration <= 0.0:
            try:
                info = sf.info(str(path))
                duration = float(info.duration)
                sample_rate = int(info.samplerate)
                channels = int(info.channels)
                ext = info.format or ext
            except Exception as e:
                logger.warning("Soundfile inspection failed for %s: %s", path, e)

        return AudioMetadata(
            duration_seconds=round(max(0.0, duration), 3),
            sample_rate=sample_rate,
            channels=channels,
            file_type=ext,
            file_size_bytes=file_size,
            bitrate=bitrate,
            title=title,
            artist=artist,
        )

    @staticmethod
    def load_audio(file_path: str | Path) -> tuple[np.ndarray, int]:
        """Loads audio file as float32 numpy array normalized to [-1.0, 1.0]."""
        path = Path(file_path)
        data, sr = sf.read(str(path), dtype="float32")
        return data, sr

    @staticmethod
    def save_audio(
        data: np.ndarray,
        sample_rate: int,
        output_path: str | Path,
        format_type: str | None = None,
    ) -> Path:
        """Saves audio data to target format (WAV, MP3, FLAC, OGG)."""
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)

        if not format_type:
            ext = out_p.suffix.lstrip(".").upper()
            format_type = "MP3" if ext == "MP3" else ("FLAC" if ext == "FLAC" else ("OGG" if ext == "OGG" else "WAV"))

        # Clip values to avoid digital distortion
        clipped = np.clip(data, -1.0, 1.0)
        sf.write(str(out_p), clipped, sample_rate, format=format_type)
        return out_p

    @classmethod
    def apply_trim(
        cls,
        data: np.ndarray,
        sample_rate: int,
        start_sec: float | None = None,
        end_sec: float | None = None,
    ) -> np.ndarray:
        total_samples = len(data)
        start_sample = 0
        end_sample = total_samples

        if start_sec is not None and start_sec > 0:
            start_sample = min(total_samples, int(start_sec * sample_rate))

        if end_sec is not None and end_sec > 0:
            end_sample = min(total_samples, int(end_sec * sample_rate))

        if start_sample >= end_sample:
            raise ValueError(
                f"Start time ({start_sec}s) must be strictly less than end time ({end_sec}s)"
            )

        return data[start_sample:end_sample].copy()

    @classmethod
    def apply_fade_in(
        cls,
        data: np.ndarray,
        sample_rate: int,
        fade_sec: float,
    ) -> np.ndarray:
        if fade_sec <= 0:
            return data
        fade_samples = min(len(data), int(fade_sec * sample_rate))
        if fade_samples <= 0:
            return data

        out = data.copy()
        curve = np.linspace(0.0, 1.0, fade_samples, dtype=np.float32)
        if out.ndim == 2:
            curve = curve[:, np.newaxis]
        out[:fade_samples] *= curve
        return out

    @classmethod
    def apply_fade_out(
        cls,
        data: np.ndarray,
        sample_rate: int,
        fade_sec: float,
    ) -> np.ndarray:
        if fade_sec <= 0:
            return data
        fade_samples = min(len(data), int(fade_sec * sample_rate))
        if fade_samples <= 0:
            return data

        out = data.copy()
        curve = np.linspace(1.0, 0.0, fade_samples, dtype=np.float32)
        if out.ndim == 2:
            curve = curve[:, np.newaxis]
        out[-fade_samples:] *= curve
        return out

    @classmethod
    def apply_volume_gain(cls, data: np.ndarray, gain_db: float) -> np.ndarray:
        if gain_db == 0.0:
            return data
        multiplier = 10.0 ** (gain_db / 20.0)
        return data * multiplier

    @classmethod
    def apply_bass_boost(
        cls,
        data: np.ndarray,
        sample_rate: int,
        boost_db: float,
        cutoff_hz: float = 250.0,
    ) -> np.ndarray:
        if boost_db == 0.0 or cutoff_hz <= 0:
            return data

        nyquist = sample_rate / 2.0
        norm_cutoff = min(0.99, max(0.01, cutoff_hz / nyquist))
        b, a = signal.butter(2, norm_cutoff, btype="low")

        gain_factor = 10.0 ** (boost_db / 20.0) - 1.0

        if data.ndim == 2:
            low_ch0 = signal.lfilter(b, a, data[:, 0])
            low_ch1 = signal.lfilter(b, a, data[:, 1])
            low = np.column_stack([low_ch0, low_ch1])
        else:
            low = signal.lfilter(b, a, data)

        return data + (low * gain_factor).astype(np.float32)

    @classmethod
    def apply_speed(
        cls,
        data: np.ndarray,
        sample_rate: int,
        speed_factor: float,
    ) -> np.ndarray:
        if abs(speed_factor - 1.0) < 1e-3 or speed_factor <= 0:
            return data

        # Limit speed to safe range [0.25x, 4.0x]
        speed = max(0.25, min(4.0, speed_factor))
        new_length = int(len(data) / speed)
        if new_length <= 0:
            return data

        resampled = signal.resample(data, new_length, axis=0)
        return resampled.astype(np.float32)

    @classmethod
    def apply_normalize(cls, data: np.ndarray, target_db: float = -0.5) -> np.ndarray:
        peak = np.max(np.abs(data))
        if peak < 1e-6:
            return data
        target_amp = 10.0 ** (target_db / 20.0)
        scale = target_amp / peak
        return data * scale

    @classmethod
    def apply_reverse(cls, data: np.ndarray) -> np.ndarray:
        return data[::-1].copy()

    @classmethod
    def apply_echo(
        cls,
        data: np.ndarray,
        sample_rate: int,
        delay_sec: float = 0.3,
        decay: float = 0.4,
    ) -> np.ndarray:
        if delay_sec <= 0 or decay <= 0:
            return data

        delay_samples = int(delay_sec * sample_rate)
        if delay_samples <= 0:
            return data

        out_len = len(data) + delay_samples
        if data.ndim == 2:
            out = np.zeros((out_len, data.shape[1]), dtype=np.float32)
            out[:len(data)] += data
            out[delay_samples:delay_samples + len(data)] += data * decay
        else:
            out = np.zeros(out_len, dtype=np.float32)
            out[:len(data)] += data
            out[delay_samples:delay_samples + len(data)] += data * decay

        return out

    @classmethod
    def process(
        cls,
        input_path: str | Path,
        output_path: str | Path,
        start_sec: float | None = None,
        end_sec: float | None = None,
        effects: AudioEffectsConfig | None = None,
        format_type: str | None = None,
    ) -> AudioMetadata:
        """Executes full audio manipulation pipeline and returns new audio metadata."""
        data, sr = cls.load_audio(input_path)

        # 1. Trim
        if start_sec is not None or end_sec is not None:
            data = cls.apply_trim(data, sr, start_sec=start_sec, end_sec=end_sec)

        # 2. Effects
        if effects is not None:
            if effects.bass_boost_db:
                data = cls.apply_bass_boost(data, sr, effects.bass_boost_db)

            if effects.volume_gain_db:
                data = cls.apply_volume_gain(data, effects.volume_gain_db)

            if effects.speed_factor:
                data = cls.apply_speed(data, sr, effects.speed_factor)

            if effects.reverse:
                data = cls.apply_reverse(data)

            if effects.echo_delay_sec:
                data = cls.apply_echo(data, sr, delay_sec=effects.echo_delay_sec, decay=effects.echo_decay)

            if effects.fade_in_sec:
                data = cls.apply_fade_in(data, sr, effects.fade_in_sec)

            if effects.fade_out_sec:
                data = cls.apply_fade_out(data, sr, effects.fade_out_sec)

            if effects.normalize:
                data = cls.apply_normalize(data)

        # 3. Save
        saved_path = cls.save_audio(data, sr, output_path, format_type=format_type)
        return cls.get_metadata(saved_path)
