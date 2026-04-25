"""Tests for social_research_probe.technologies.media_fetch.youtube_api.

Covers _build_client, _search_videos, _fetch_video_details, _fetch_channel_details using
mock API clients — no live network calls.
"""

from __future__ import annotations

import pytest
from social_research_probe.utils.core.errors import AdapterError

import social_research_probe.technologies.media_fetch.youtube_api as fetch


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
    monkeypatch.setattr(fetch, "_build_client", lambda key: _MockClient(search_resp={"items": items}))
    result = fetch._search_videos("fake-key", topic="ai", max_items=5, published_after=None)
    assert result == items


def test_search_videos_handles_non_list_items(monkeypatch):
    """_search_videos returns an empty list when the API payload is malformed."""
    monkeypatch.setattr(fetch, "_build_client", lambda key: _MockClient(search_resp={"items": "not-a-list"}))
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


def test_fetch_video_details_returns_items(monkeypatch):
    """_fetch_video_details returns the items list from the videos.list response."""
    items = [{"id": "abc"}]
    monkeypatch.setattr(fetch, "_build_client", lambda key: _MockClient(videos_resp={"items": items}))
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
    monkeypatch.setattr(fetch, "_build_client", lambda key: _MockClient(channels_resp={"items": items}))
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
