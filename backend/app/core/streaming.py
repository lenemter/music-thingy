from __future__ import annotations

import mimetypes
import os
from pathlib import Path
from typing import Generator

from fastapi import HTTPException, Request, status
from fastapi.responses import StreamingResponse


def range_stream_response(file_path: str | Path, request: Request) -> StreamingResponse:
    path = Path(file_path)
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    file_size = path.stat().st_size
    content_type, _ = mimetypes.guess_type(str(path))
    if not content_type:
        ext = path.suffix.lower()
        content_type = {
            ".mp3": "audio/mpeg",
            ".wav": "audio/wav",
            ".flac": "audio/flac",
            ".ogg": "audio/ogg",
            ".m4a": "audio/mp4",
        }.get(ext, "application/octet-stream")

    range_header = request.headers.get("range")
    if not range_header:
        def iter_full() -> Generator[bytes, None, None]:
            with open(path, "rb") as f:
                while chunk := f.read(64 * 1024):
                    yield chunk

        headers = {
            "Content-Length": str(file_size),
            "Accept-Ranges": "bytes",
            "Content-Disposition": f'inline; filename="{path.name}"',
        }
        return StreamingResponse(iter_full(), status_code=status.HTTP_200_OK, media_type=content_type, headers=headers)

    # Parse range header: e.g. "bytes=0-1024" or "bytes=1024-"
    try:
        unit, _, r_val = range_header.strip().partition("=")
        if unit != "bytes":
            raise ValueError()
        start_str, _, end_str = r_val.partition("-")
        start = int(start_str) if start_str else 0
        end = int(end_str) if end_str else file_size - 1
        if end >= file_size:
            end = file_size - 1
        if start > end or start >= file_size:
            raise ValueError()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
            detail="Requested range not satisfiable",
            headers={"Content-Range": f"bytes */{file_size}"},
        )

    content_length = end - start + 1

    def iter_range() -> Generator[bytes, None, None]:
        with open(path, "rb") as f:
            f.seek(start)
            remaining = content_length
            while remaining > 0:
                chunk_size = min(64 * 1024, remaining)
                data = f.read(chunk_size)
                if not data:
                    break
                remaining -= len(data)
                yield data

    headers = {
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(content_length),
        "Content-Disposition": f'inline; filename="{path.name}"',
    }
    return StreamingResponse(
        iter_range(),
        status_code=status.HTTP_206_PARTIAL_CONTENT,
        media_type=content_type,
        headers=headers,
    )
