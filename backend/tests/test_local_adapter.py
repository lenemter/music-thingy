from services.music.dto import SearchType, Service
from services.music.local import LocalFilesAdapter, LocalUpload

UPLOADS = [
    LocalUpload(id=1, title="Моя песня", artist="Я", duration_seconds=120,
                audio_url="/api/uploads/1/stream?sig=x", cover="template:2"),
    LocalUpload(id=2, title="Другое", artist="Кто-то", duration_seconds=0,
                audio_url="/api/uploads/2/stream?sig=y"),
]


def test_search_by_title_and_artist():
    a = LocalFilesAdapter(UPLOADS)
    assert [t.service_id for t in a.search("песня").tracks] == ["1"]
    assert [t.service_id for t in a.search("кто-то").tracks] == ["2"]
    assert a.search("нет такого").tracks == ()


def test_track_fields():
    t = LocalFilesAdapter(UPLOADS).get_track("1")
    assert t.service == Service.LOCAL
    assert t.duration_ms == 120000
    assert t.direct_audio_url == "/api/uploads/1/stream?sig=x"
    assert t.artwork_url == "template:2"
    assert LocalFilesAdapter(UPLOADS).get_track("2").duration_ms is None


def test_unsupported_types_and_empty_query():
    a = LocalFilesAdapter(UPLOADS)
    assert a.search("песня", types=frozenset({SearchType.ALBUM})).tracks == ()
    assert a.search("  ").tracks == ()
    assert a.get_track("999") is None
    assert a.set_track_like("1", True) is True
    assert a.set_track_like("1", False) is True
