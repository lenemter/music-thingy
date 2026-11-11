from __future__ import annotations

import base64
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import mutagen
from mutagen.flac import Picture

logger = logging.getLogger(__name__)


@dataclass
class AudioMetadata:
    duration_seconds: int = 0
    title: str | None = None
    artist: str | None = None
    cover_bytes: bytes | None = None
    cover_mime: str | None = None


def extract_audio_metadata(file_path: Path | str) -> AudioMetadata:
    """Extract duration, title, artist, and embedded cover art using Mutagen."""
    path_str = str(file_path)
    meta = AudioMetadata()

    try:
        audio = mutagen.File(path_str)
        if audio is None:
            return meta

        # Duration
        if hasattr(audio, "info") and audio.info and hasattr(audio.info, "length"):
            meta.duration_seconds = max(0, int(round(audio.info.length)))

        tags: Any = getattr(audio, "tags", None)

        # 1. ID3 tags (MP3, AIFF)
        if tags and hasattr(tags, "getall"):
            tit2 = tags.get("TIT2")
            if tit2 and hasattr(tit2, "text") and tit2.text:
                meta.title = str(tit2.text[0]).strip() or None

            tpe1 = tags.get("TPE1")
            if tpe1 and hasattr(tpe1, "text") and tpe1.text:
                meta.artist = str(tpe1.text[0]).strip() or None

            apics = tags.getall("APIC")
            if apics:
                first_apic = apics[0]
                meta.cover_bytes = getattr(first_apic, "data", None)
                meta.cover_mime = getattr(first_apic, "mime", "image/jpeg")

        # 2. MP4 / M4A / AAC tags
        elif tags and hasattr(tags, "get") and "\xa9nam" in tags:
            nam = tags.get("\xa9nam")
            if nam:
                meta.title = str(nam[0]).strip() or None

            art = tags.get("\xa9ART")
            if art:
                meta.artist = str(art[0]).strip() or None

            covr = tags.get("covr")
            if covr and len(covr) > 0:
                first_covr = covr[0]
                meta.cover_bytes = bytes(first_covr)
                meta.cover_mime = "image/jpeg"

        # 3. VorbisComment (FLAC, OGG)
        elif tags and hasattr(tags, "get"):
            t = tags.get("title")
            if t:
                meta.title = str(t[0]).strip() or None

            a = tags.get("artist")
            if a:
                meta.artist = str(a[0]).strip() or None

        # 4. FLAC pictures attribute
        if not meta.cover_bytes and hasattr(audio, "pictures") and audio.pictures:
            first_pic = audio.pictures[0]
            meta.cover_bytes = first_pic.data
            meta.cover_mime = first_pic.mime or "image/jpeg"

        # 5. OGG metadata_block_picture
        if not meta.cover_bytes and tags and hasattr(tags, "get"):
            mbp = tags.get("metadata_block_picture")
            if mbp:
                try:
                    raw_data = base64.b64decode(mbp[0])
                    pic = Picture(raw_data)
                    meta.cover_bytes = pic.data
                    meta.cover_mime = pic.mime or "image/jpeg"
                except Exception:
                    pass

    except Exception as e:
        logger.warning("Could not extract metadata from %s: %s", path_str, e)

    return meta
