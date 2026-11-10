import pytest
from services.music.dto import (
    AlbumDTO,
    ArtistDTO,
    ErrorKind,
    PlaybackDTO,
    PlaybackKind,
    PlaylistDTO,
    SearchResultDTO,
    SearchType,
    Service,
    ServiceErrorDTO,
    TrackDTO,
)


def test_playback_dto():
    pb = PlaybackDTO(kind=PlaybackKind.YANDEX_IFRAME, ref="123/456")
    assert pb.kind == PlaybackKind.YANDEX_IFRAME
    assert pb.ref == "123/456"


def test_track_dto_creation_and_frontend_dict():
    pb = PlaybackDTO(kind=PlaybackKind.YANDEX_IFRAME, ref="87491164/16916643")
    track = TrackDTO(
        service=Service.YANDEX,
        service_id="87491164:16916643",
        title="Queen",
        artists=("KVPV", "DJ X"),
        artist_ids=("101", "102"),
        duration_ms=157710,
        album="Greatest Hits",
        playback=pb,
        direct_audio_url="https://api.music.yandex.net/get-mp3/test.mp3",
        artwork_url="https://avatars.yandex.net/get-music-content/test/400x400",
        external_url="https://music.yandex.ru/album/16916643/track/87491164",
        sources=("ЯМ",),
    )

    assert track.artist_display == "KVPV, DJ X"
    assert track.duration_seconds == 157
    assert track.track_key == "yandex:87491164:16916643"

    frontend_dict = track.to_frontend_dict(numeric_id=42)
    assert frontend_dict["id"] == 42
    assert frontend_dict["title"] == "Queen"
    assert frontend_dict["artist"] == "KVPV, DJ X"
    assert frontend_dict["artists"] == ["KVPV", "DJ X"]
    assert frontend_dict["duration"] == 157
    assert frontend_dict["sources"] == ["ЯМ"]
    assert frontend_dict["source"] == "ЯМ"
    assert frontend_dict["service"] == "yandex"
    assert frontend_dict["service_id"] == "87491164:16916643"
    assert frontend_dict["direct_audio_url"] == "https://api.music.yandex.net/get-mp3/test.mp3"
    assert frontend_dict["playback"]["kind"] == "yandex_iframe"
    assert frontend_dict["playback"]["ref"] == "87491164/16916643"


def test_track_dto_artist_ids_mismatch():
    with pytest.raises(ValueError, match="artist_ids and artists must have the same length"):
        TrackDTO(
            service=Service.YANDEX,
            service_id="1",
            title="Song",
            artists=("Artist 1", "Artist 2"),
            artist_ids=("101",),
        )


def test_album_dto():
    track = TrackDTO(
        service=Service.YANDEX,
        service_id="10:20",
        title="Track 1",
        artists=("Band",),
        duration_ms=200000,
    )
    album = AlbumDTO(
        service=Service.YANDEX,
        service_id="20",
        title="First Album",
        artist="Band",
        year=2024,
        tracks_count=1,
        artwork_url="https://cover.url",
        tracks=(track,),
    )

    f_dict = album.to_frontend_dict(numeric_id=99)
    assert f_dict["id"] == 99
    assert f_dict["title"] == "First Album"
    assert f_dict["artist"] == "Band"
    assert f_dict["year"] == 2024
    assert f_dict["tracks_count"] == 1
    assert len(f_dict["tracks"]) == 1
    assert f_dict["tracks"][0]["title"] == "Track 1"


def test_playlist_dto():
    playlist = PlaylistDTO(
        service=Service.YANDEX,
        service_id="user123:3",
        title="Night Drive",
        description="Cool vibes",
        owner_name="Leo",
        tracks_count=15,
        artwork_url="https://playlist.cover",
    )
    f_dict = playlist.to_frontend_dict()
    assert f_dict["name"] == "Night Drive"
    assert f_dict["title"] == "Night Drive"
    assert f_dict["description"] == "Cool vibes"
    assert f_dict["owner_name"] == "Leo"
    assert f_dict["tracks_count"] == 15


def test_artist_dto():
    artist = ArtistDTO(
        service=Service.YANDEX,
        service_id="777",
        name="Queen",
        genres=("rock", "classic rock"),
        artwork_url="https://artist.cover",
    )
    assert artist.service == Service.YANDEX
    assert artist.name == "Queen"
    assert "rock" in artist.genres


def test_search_result_dto():
    err = ServiceErrorDTO(
        service=Service.SPOTIFY,
        kind=ErrorKind.NOT_SUPPORTED,
        message="Not implemented",
    )
    res = SearchResultDTO(query="Queen", errors=(err,))
    assert res.query == "Queen"
    assert len(res.errors) == 1
    assert res.errors[0].kind == ErrorKind.NOT_SUPPORTED
