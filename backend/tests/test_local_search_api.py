"""Интеграция локальных файлов (загрузок пользователя) с поиском."""
import pytest
from fastapi.testclient import TestClient

from app.config import settings
from services.music.aggregator import MusicAggregator
from services.music.dto import Service
from services.music.local import LocalFilesAdapter, LocalUpload


@pytest.fixture(autouse=True)
def isolated_upload_dir(tmp_path, monkeypatch):
    """Загрузки из тестов не должны попадать в настоящую папку uploads."""
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))


def auth_headers(client: TestClient, email: str) -> dict[str, str]:
    client.post(
        "/api/auth/register",
        json={"email": email, "password": "password12345", "display_name": "Local User"},
    )
    token = client.post(
        "/api/auth/token", json={"email": email, "password": "password12345"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def upload_file(client: TestClient, headers: dict[str, str], title: str) -> dict:
    resp = client.post(
        "/api/uploads",
        headers=headers,
        files={"file": ("song.mp3", b"\x00" * 64, "audio/mpeg")},
        data={"title": title, "artist": "Tester"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def search_local(client: TestClient, q: str, headers: dict[str, str] | None = None) -> dict:
    resp = client.get(
        "/api/music/search",
        params={"q": q, "services": "local"},
        headers=headers or {},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


# ---------- уровень API ----------

def test_search_finds_own_upload(client: TestClient):
    headers = auth_headers(client, "local_owner@example.com")
    upload = upload_file(client, headers, "Моя песня")

    data = search_local(client, "песня", headers)

    assert len(data["tracks"]) == 1
    track = data["tracks"][0]
    assert track["service"] == "local"
    assert track["service_id"] == str(upload["id"])
    assert track["title"] == "Моя песня"
    assert track["source"] == "ФАЙЛ"
    assert "sig=" in track["direct_audio_url"]
    assert data["errors"] == []


def test_search_does_not_match_other_titles(client: TestClient):
    headers = auth_headers(client, "local_nomatch@example.com")
    upload_file(client, headers, "Моя песня")
    assert search_local(client, "совсем другое", headers)["tracks"] == []


def test_search_hides_uploads_of_other_users(client: TestClient):
    owner = auth_headers(client, "local_owner2@example.com")
    stranger = auth_headers(client, "local_stranger@example.com")
    upload_file(client, owner, "Секретная песня")

    assert search_local(client, "секретная", stranger)["tracks"] == []


def test_search_anonymous_gets_no_local_tracks(client: TestClient):
    owner = auth_headers(client, "local_owner3@example.com")
    upload_file(client, owner, "Приватная песня")

    assert search_local(client, "приватная")["tracks"] == []


def test_search_marks_liked_upload(client: TestClient):
    headers = auth_headers(client, "local_liker@example.com")
    upload = upload_file(client, headers, "Любимая песня")

    like = client.put(f"/api/music/tracks/local/{upload['id']}/like", json={}, headers=headers)
    assert like.status_code == 200
    like_data = like.json()
    assert like_data["title"] == "Любимая песня"
    assert like_data["source"] == "ФАЙЛ"
    assert like_data["synced"] is True
    assert "sig=" in like_data["direct_audio_url"]

    track = search_local(client, "любимая", headers)["tracks"][0]
    assert track["liked"] is True

    liked = client.get("/api/music/me/liked", headers=headers).json()
    assert len(liked) == 1
    assert liked[0]["service"] == "local"
    assert liked[0]["service_id"] == str(upload["id"])
    assert liked[0]["source"] == "ФАЙЛ"
    assert "sig=" in liked[0]["direct_audio_url"]

    unlike = client.delete(f"/api/music/tracks/local/{upload['id']}/like", headers=headers)
    assert unlike.status_code == 200
    assert unlike.json()["liked"] is False
    assert unlike.json()["synced"] is True


def test_local_track_playback_and_stream_use_adapter(client: TestClient):
    owner = auth_headers(client, "local_player@example.com")
    stranger = auth_headers(client, "local_other@example.com")
    upload = upload_file(client, owner, "Трек для плеера")

    track_resp = client.get(f"/api/music/tracks/local/{upload['id']}", headers=owner)
    assert track_resp.status_code == 200
    track = track_resp.json()
    assert track["service"] == "local"
    assert track["title"] == "Трек для плеера"
    assert track["source"] == "ФАЙЛ"
    assert "sig=" in track["direct_audio_url"]

    pb_resp = client.get(f"/api/music/playback/local/{upload['id']}", headers=owner)
    assert pb_resp.status_code == 200
    pb = pb_resp.json()
    assert pb["kind"] == "direct_url"
    assert f"/api/uploads/{upload['id']}/stream?sig=" in pb["ref"]

    stream_resp = client.get(
        f"/api/music/tracks/local/{upload['id']}/stream",
        headers=owner,
        follow_redirects=False,
    )
    assert stream_resp.status_code == 307
    assert f"/api/uploads/{upload['id']}/stream?sig=" in stream_resp.headers["location"]

    assert client.get(f"/api/music/tracks/local/{upload['id']}", headers=stranger).status_code == 404
    assert client.get(f"/api/music/playback/local/{upload['id']}").status_code == 404
    assert client.get(f"/api/music/tracks/local/{upload['id']}/stream").status_code == 404


# ---------- уровень агрегатора ----------

UPLOADS = [
    LocalUpload(id=1, title="Моя песня", artist="Я", duration_seconds=120,
                audio_url="/api/uploads/1/stream?sig=x"),
]


@pytest.mark.asyncio
async def test_aggregator_searches_user_local_adapter_by_default():
    """Без явного списка сервисов адаптер из user_adapters всё равно участвует в поиске."""
    agg = MusicAggregator()
    agg._adapters.clear()

    result = await agg.search("песня", user_adapters={Service.LOCAL: LocalFilesAdapter(UPLOADS)})

    assert [t.service_id for t in result.tracks] == ["1"]
    assert result.tracks[0].sources == ("ФАЙЛ",)
    assert result.tracks[0].to_frontend_dict()["source"] == "ФАЙЛ"


@pytest.mark.asyncio
async def test_aggregator_reports_missing_local_adapter():
    agg = MusicAggregator()
    agg._adapters.clear()

    result = await agg.search("песня", services=["local"])

    assert result.tracks == ()
    assert any(e.service == Service.LOCAL for e in result.errors)
