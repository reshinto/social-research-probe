"""Tests for social_research_probe.technologies.media_fetch.youtube_api.

Covers _build_client, _search_videos, _fetch_video_details, _fetch_channel_details using
mock API clients — no live network calls.
"""

from __future__ import annotations

import pytest

import social_research_probe.technologies.media_fetch.youtube_api as fetch
from social_research_probe.utils.core.errors import AdapterError


class _MockExecute:
    def __init__(self, response: dict) -> None:
        self._response = response

    def execute(self):
        return self._response


class _MockList:
    def __init__(self, response: dict) -> None:
        self._response = response

    def list(self, **kwargs):
        return _MockExecute(self._response)


class _MockClient:
    def __init__(self, search_resp=None, videos_resp=None, channels_resp=None):
        self._search_resp = search_resp or {"items": []}
        self._videos_resp = videos_resp or {"items": []}
        self._channels_resp = channels_resp or {"items": []}

    def search(self):
        return _MockList(self._search_resp)

    def videos(self):
        return _MockList(self._videos_resp)

    def channels(self):
        return _MockList(self._channels_resp)


def test_build_client_calls_discovery(monkeypatch):
    """_build_client delegates to googleapiclient.discovery.build."""
    import sys
    import types

    sentinel = object()
    fake_discovery = types.ModuleType("googleapiclient.discovery")
    fake_discovery.build = lambda service, version, **kw: sentinel
    fake_gac = types.ModuleType("googleapiclient")
    fake_gac.discovery = fake_discovery
    monkeypatch.setitem(sys.modules, "googleapiclient", fake_gac)
    monkeypatch.setitem(sys.modules, "googleapiclient.discovery", fake_discovery)

    result = fetch._build_client("test-api-key")
    assert result is sentinel


def test_search_videos_returns_items(monkeypatch):
    """_search_videos returns the items list from the API response."""
    items = [{"id": {"videoId": "abc"}}]
    monkeypatch.setattr(
        fetch, "_build_client", lambda key: _MockClient(search_resp={"items": items})
    )
    result = fetch._search_videos("fake-key", topic="ai", max_items=5, published_after=None)
    assert result == items


def test_search_videos_handles_non_list_items(monkeypatch):
    """_search_videos returns an empty list when the API payload is malformed."""
    monkeypatch.setattr(
        fetch, "_build_client", lambda key: _MockClient(search_resp={"items": "not-a-list"})
    )
    result = fetch._search_videos("fake-key", topic="ai", max_items=5, published_after=None)
    assert result == []


def test_search_videos_raises_adapter_error_on_exception(monkeypatch):
    """_search_videos wraps API exceptions in AdapterError."""

    class _FailingClient:
        def search(self):
            raise RuntimeError("network error")

    monkeypatch.setattr(fetch, "_build_client", lambda key: _FailingClient())
    with pytest.raises(AdapterError, match="youtube search failed"):
        fetch._search_videos("fake-key", topic="ai", max_items=5, published_after=None)


def test_search_youtube_uses_cache_on_second_call(tmp_path, monkeypatch):
    """search_youtube writes and reuses the YouTube search cache."""
    monkeypatch.setenv("SRP_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("SRP_DISABLE_CACHE", raising=False)
    monkeypatch.setattr(fetch, "resolve_youtube_api_key", lambda: "fake-key")
    calls = 0

    def fake_search(api_key, *, topic, max_items, published_after):
        nonlocal calls
        calls += 1
        return [{"id": {"videoId": "abc"}}]

    monkeypatch.setattr(fetch, "_search_videos", fake_search)

    first = fetch.search_youtube("ai", max_items=5, published_after=None)
    second = fetch.search_youtube("ai", max_items=5, published_after=None)

    assert calls == 1
    assert first == second == [{"id": {"videoId": "abc"}}]
    assert list((tmp_path / "cache" / "stages" / "youtube_search").glob("*.json"))


def test_fetch_video_details_returns_items(monkeypatch):
    """_fetch_video_details returns the items list from the videos.list response."""
    items = [{"id": "abc"}]
    monkeypatch.setattr(
        fetch, "_build_client", lambda key: _MockClient(videos_resp={"items": items})
    )
    result = fetch._fetch_video_details("fake-key", video_ids=["abc"])
    assert result == items


def test_fetch_video_details_raises_adapter_error_on_exception(monkeypatch):
    """_fetch_video_details wraps API exceptions in AdapterError."""

    class _FailingClient:
        def videos(self):
            raise RuntimeError("api error")

    monkeypatch.setattr(fetch, "_build_client", lambda key: _FailingClient())
    with pytest.raises(AdapterError, match=r"youtube videos\.list failed"):
        fetch._fetch_video_details("fake-key", video_ids=["x"])


def test_fetch_channel_details_returns_items(monkeypatch):
    """_fetch_channel_details returns the items list from the channels.list response."""
    items = [{"id": "UC123"}]
    monkeypatch.setattr(
        fetch, "_build_client", lambda key: _MockClient(channels_resp={"items": items})
    )
    result = fetch._fetch_channel_details("fake-key", channel_ids=["UC123"])
    assert result == items


def test_fetch_channel_details_raises_adapter_error_on_exception(monkeypatch):
    """_fetch_channel_details wraps API exceptions in AdapterError."""

    class _FailingClient:
        def channels(self):
            raise RuntimeError("api error")

    monkeypatch.setattr(fetch, "_build_client", lambda key: _FailingClient())
    with pytest.raises(AdapterError, match=r"youtube channels\.list failed"):
        fetch._fetch_channel_details("fake-key", channel_ids=["UC123"])


@pytest.mark.asyncio
async def test_hydrate_youtube_uses_cache_on_second_call(tmp_path, monkeypatch):
    """hydrate_youtube writes and reuses the YouTube hydrate cache."""
    monkeypatch.setenv("SRP_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("SRP_DISABLE_CACHE", raising=False)
    monkeypatch.setattr(fetch, "resolve_youtube_api_key", lambda: "fake-key")
    calls = {"videos": 0, "channels": 0}

    def fake_videos(api_key, *, video_ids):
        calls["videos"] += 1
        return [{"id": video_ids[0]}]

    def fake_channels(api_key, *, channel_ids):
        calls["channels"] += 1
        return [{"id": channel_ids[0]}]

    monkeypatch.setattr(fetch, "_fetch_video_details", fake_videos)
    monkeypatch.setattr(fetch, "_fetch_channel_details", fake_channels)

    first = await fetch.hydrate_youtube(["abc"], ["UC123"])
    second = await fetch.hydrate_youtube(["abc"], ["UC123"])

    assert calls == {"videos": 1, "channels": 1}
    assert first == second == ([{"id": "abc"}], [{"id": "UC123"}])
    assert list((tmp_path / "cache" / "stages" / "youtube_hydrate").glob("*.json"))
