import pytest
from fastapi.testclient import TestClient


def test_music_search_multi_service(client: TestClient):
    resp = client.get("/api/music/search", params={"q": "Queen", "limit": 2})
    assert resp.status_code == 200
    data = resp.json()
    assert "query" in data
    assert data["query"] == "Queen"
    assert "tracks" in data
    assert isinstance(data["tracks"], list)
    assert len(data["tracks"]) > 0

    track = data["tracks"][0]
    assert "id" in track
    assert "title" in track
    assert "artist" in track
    assert "cover" in track
    assert "duration" in track
    assert "sources" in track
    assert "source" in track


def test_music_get_track_and_playback(client: TestClient):
    # Search first
    resp = client.get("/api/music/search", params={"q": "Rock", "services": "spotify,youtube", "limit": 1})
    assert resp.status_code == 200
    tracks = resp.json()["tracks"]
    assert len(tracks) > 0

    first = tracks[0]
    srv = first["service"]
    s_id = first["service_id"]

    # Get track
    t_resp = client.get(f"/api/music/tracks/{srv}/{s_id}")
    assert t_resp.status_code == 200
    t_data = t_resp.json()
    assert t_data["service_id"] == s_id
    assert t_data["service"] == srv

    # Get playback
    p_resp = client.get(f"/api/music/playback/{srv}/{s_id}")
    assert p_resp.status_code == 200
    p_data = p_resp.json()
    assert "kind" in p_data
    assert "ref" in p_data
