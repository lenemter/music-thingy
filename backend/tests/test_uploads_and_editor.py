import io
import numpy as np
import pytest
import soundfile as sf
from fastapi.testclient import TestClient


def _get_auth_headers(client: TestClient) -> dict[str, str]:
    email = "audio_user@example.com"
    pwd = "password123"
    client.post("/api/auth/register", json={"email": email, "password": pwd, "display_name": "Audio Producer"})
    resp = client.post("/api/auth/token", json={"email": email, "password": pwd})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_test_audio_bytes(duration_sec: float = 2.0, sample_rate: int = 44100) -> bytes:
    t = np.linspace(0, duration_sec, int(sample_rate * duration_sec), endpoint=False)
    data = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    buf = io.BytesIO()
    sf.write(buf, data, sample_rate, format="WAV")
    buf.seek(0)
    return buf.read()


def test_upload_streaming_and_audio_editor(client: TestClient):
    headers = _get_auth_headers(client)
    audio_bytes = _create_test_audio_bytes(duration_sec=3.0)

    # 1. Upload audio file
    files = {"file": ("demo_garage_v1.wav", audio_bytes, "audio/wav")}
    data = {"title": "демо_гараж_v1", "artist": "My Band"}
    resp = client.post("/api/uploads", files=files, data=data, headers=headers)
    assert resp.status_code == 201
    file_info = resp.json()
    upload_id = file_info["id"]

    assert file_info["name"] == "демо_гараж_v1"
    assert file_info["type"] == "WAV"
    assert file_info["duration"] >= 2
    assert "audio_url" in file_info
    assert file_info["is_edited"] is False

    # 2. List uploads
    list_resp = client.get("/api/uploads", headers=headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    # 3. Stream audio with full and partial content (HTTP Range)
    full_stream = client.get(f"/api/uploads/{upload_id}/stream")
    assert full_stream.status_code == 200
    assert full_stream.headers.get("accept-ranges") == "bytes"

    range_stream = client.get(
        f"/api/uploads/{upload_id}/stream",
        headers={"Range": "bytes=0-1024"},
    )
    assert range_stream.status_code == 206
    assert "bytes 0-1024/" in range_stream.headers.get("content-range", "")
    assert len(range_stream.content) == 1025

    # 4. Trim audio in editor
    trim_resp = client.post(
        "/api/editor/trim",
        json={
            "upload_id": upload_id,
            "start_sec": 0.5,
            "end_sec": 2.0,
            "save_as_new": True,
            "new_name": "демо_гараж_trimmed",
        },
        headers=headers,
    )
    assert trim_resp.status_code == 200
    trimmed_info = trim_resp.json()
    assert trimmed_info["name"] == "демо_гараж_trimmed"
    assert trimmed_info["is_edited"] is True
    assert trimmed_info["duration"] <= 2
    trimmed_id = trimmed_info["id"]

    # 5. Apply audio effects (fade + bass boost + gain + normalize)
    fx_resp = client.post(
        "/api/editor/effects",
        json={
            "upload_id": trimmed_id,
            "fade_in_sec": 0.2,
            "fade_out_sec": 0.2,
            "bass_boost_db": 3.0,
            "volume_gain_db": 1.5,
            "normalize": True,
            "save_as_new": True,
            "new_name": "демо_гараж_mastered",
        },
        headers=headers,
    )
    assert fx_resp.status_code == 200
    fx_info = fx_resp.json()
    assert fx_info["name"] == "демо_гараж_mastered"
    assert fx_info["is_edited"] is True
    assert "Bass" in fx_info["edit_summary"]

    # 6. Combined audio process pipeline
    proc_resp = client.post(
        "/api/editor/process",
        json={
            "upload_id": upload_id,
            "start_sec": 0.2,
            "end_sec": 1.8,
            "bass_boost_db": 4.0,
            "speed_factor": 1.1,
            "normalize": True,
            "save_as_new": True,
            "new_name": "демо_full_pipeline",
        },
        headers=headers,
    )
    assert proc_resp.status_code == 200
    proc_info = proc_resp.json()
    assert proc_info["is_edited"] is True

    # 7. Delete original upload
    del_resp = client.delete(f"/api/uploads/{upload_id}", headers=headers)
    assert del_resp.status_code == 204
