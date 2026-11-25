import pytest

from services.music.base import AdapterError, BaseMusicAdapter
from services.music.dto import ErrorKind, SearchResultDTO, Service


class MinimalAdapter(BaseMusicAdapter):
    service = Service.LOCAL

    def __init__(self) -> None:
        self.closed = False

    def search(self, query, types=frozenset(), limit=10):
        return SearchResultDTO(query=query)

    def get_track(self, service_id):
        return None

    def get_playlist(self, service_id):
        return None

    def get_artist(self, service_id):
        return None

    def close(self) -> None:
        self.closed = True


def test_base_adapter_is_abstract():
    with pytest.raises(TypeError):
        BaseMusicAdapter()  # type: ignore[abstract]


def test_optional_methods_have_safe_defaults():
    adapter = MinimalAdapter()
    assert adapter.get_album("1") is None
    assert adapter.get_user_playlists() == []
    assert adapter.get_user_favorites() == []
    assert adapter.set_track_like("1", True) is False
    assert MinimalAdapter.create_from_credentials(token="t") is None
    assert MinimalAdapter.official is True


def test_context_manager_closes_adapter():
    with MinimalAdapter() as adapter:
        assert adapter.closed is False
    assert adapter.closed is True


def test_adapter_error_carries_kind_and_status():
    err = AdapterError(ErrorKind.RATE_LIMIT, "slow down", 429)
    assert str(err) == "slow down"
    assert err.kind == ErrorKind.RATE_LIMIT
    assert err.status_code == 429
    assert AdapterError(ErrorKind.UNKNOWN, "x").status_code is None
