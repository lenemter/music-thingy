from unittest.mock import MagicMock
import pytest

from services.music.aggregator import MusicAggregator
from services.music.base import BaseMusicAdapter
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
    TrackDTO,
)


class DummyMockAdapter(BaseMusicAdapter):
    service = Service.YANDEX

    def search(self, query: str, types=frozenset({SearchType.TRACK}), limit: int = 10):
        track = TrackDTO(
            service=Service.YANDEX,
            service_id="101",
            title="Song A",
            artists=("Artist 1",),
            sources=("ЯМ",),
        )
        return SearchResultDTO(query=query, tracks=(track,))

    def get_track(self, service_id: str):
        if service_id == "101":
            return TrackDTO(
                service=Service.YANDEX,
                service_id="101",
                title="Song A",
                artists=("Artist 1",),
                sources=("ЯМ",),
            )
        return None

    def get_album(self, service_id: str):
        if service_id == "201":
            return AlbumDTO(
                service=Service.YANDEX,
                service_id="201",
                title="Album A",
                artist="Artist 1",
            )
        return None

    def get_artist(self, service_id: str):
        if service_id == "301":
            return ArtistDTO(
                service=Service.YANDEX,
                service_id="301",
                name="Artist 1",
            )
        return None

    def get_playlist(self, service_id: str):
        if service_id == "401:1":
            return PlaylistDTO(
                service=Service.YANDEX,
                service_id="401:1",
                title="Playlist A",
            )
        return None


@pytest.fixture
def mock_aggregator():
    agg = MusicAggregator()
    agg._adapters.clear()
    agg.register_adapter(DummyMockAdapter())
    return agg


def test_services_status(mock_aggregator):
    statuses = mock_aggregator.get_services_status()
    assert len(statuses) == 4
    status_by_code = {s["code"]: s["online"] for s in statuses}
    assert status_by_code["ЯМ"] is True
    assert status_by_code["SP"] is False
    assert status_by_code["SC"] is False
    assert status_by_code["YT"] is False


@pytest.mark.asyncio
async def test_search_all_services(mock_aggregator):
    result = await mock_aggregator.search("Song A")
    assert result.query == "Song A"
    assert len(result.tracks) == 1
    assert result.tracks[0].title == "Song A"
    # Unimplemented services are reported in errors without crashing
    assert len(result.errors) == 3
    err_services = {e.service for e in result.errors}
    assert Service.SPOTIFY in err_services
    assert Service.SOUNDCLOUD in err_services
    assert Service.YOUTUBE in err_services


@pytest.mark.asyncio
async def test_search_single_service(mock_aggregator):
    result = await mock_aggregator.search("Song A", services=["yandex"])
    assert len(result.tracks) == 1
    assert len(result.errors) == 0


@pytest.mark.asyncio
async def test_get_track(mock_aggregator):
    track = await mock_aggregator.get_track("yandex", "101")
    assert track is not None
    assert track.title == "Song A"

    not_found = await mock_aggregator.get_track("yandex", "999")
    assert not_found is None

    no_service = await mock_aggregator.get_track("spotify", "101")
    assert no_service is None


@pytest.mark.asyncio
async def test_get_album(mock_aggregator):
    album = await mock_aggregator.get_album("yandex", "201")
    assert album is not None
    assert album.title == "Album A"


@pytest.mark.asyncio
async def test_get_artist(mock_aggregator):
    artist = await mock_aggregator.get_artist("yandex", "301")
    assert artist is not None
    assert artist.name == "Artist 1"


@pytest.mark.asyncio
async def test_get_playlist(mock_aggregator):
    playlist = await mock_aggregator.get_playlist("yandex", "401:1")
    assert playlist is not None
    assert playlist.title == "Playlist A"


def test_track_deduplication(mock_aggregator):
    t1 = TrackDTO(
        service=Service.YANDEX,
        service_id="1",
        title="Bohemian Rhapsody",
        artists=("Queen",),
        sources=("ЯМ",),
    )
    t2 = TrackDTO(
        service=Service.SPOTIFY,
        service_id="2",
        title="Bohemian Rhapsody",
        artists=("Queen",),
        sources=("SP",),
    )
    merged = mock_aggregator._aggregate_tracks([t1, t2])
    assert len(merged) == 1
    assert set(merged[0].sources) == {"ЯМ", "SP"}
