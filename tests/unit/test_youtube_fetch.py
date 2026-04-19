"""Tests for social_research_probe.platforms.youtube.fetch.

Covers build_client, search_videos, hydrate_videos, hydrate_channels using
mock API clients — no live network calls.
"""

from __future__ import annotations

import pytest

from social_research_probe.errors import AdapterError
from social_research_probe.platforms.youtube import fetch


class _MockExecute:
    """Callable that returns a fixed response dict."""

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
    """build_client delegates to googleapiclient.discovery.build."""
    import sys
    import types

    sentinel = object()
    fake_discovery = types.ModuleType("googleapiclient.discovery")
    fake_discovery.build = lambda service, version, **kw: sentinel
    fake_gac = types.ModuleType("googleapiclient")
    fake_gac.discovery = fake_discovery
    monkeypatch.setitem(sys.modules, "googleapiclient", fake_gac)
    monkeypatch.setitem(sys.modules, "googleapiclient.discovery", fake_discovery)

    result = fetch.build_client("test-api-key")
    assert result is sentinel


def test_search_videos_returns_items():
    """search_videos returns the items list from the API response."""
    items = [{"id": {"videoId": "abc"}}]
    client = _MockClient(search_resp={"items": items})
    result = fetch.search_videos(client, topic="ai", max_items=5, published_after=None)
    assert result == items


def test_search_videos_handles_non_list_items():
    """search_videos returns an empty list when the API payload is malformed."""
    client = _MockClient(search_resp={"items": "not-a-list"})
    result = fetch.search_videos(client, topic="ai", max_items=5, published_after=None)
    assert result == []


def test_search_videos_raises_adapter_error_on_exception():
    """search_videos wraps API exceptions in AdapterError."""

    class _FailingClient:
        def search(self):
            raise RuntimeError("network error")

    with pytest.raises(AdapterError, match="youtube search failed"):
        fetch.search_videos(_FailingClient(), topic="ai", max_items=5, published_after=None)


def test_hydrate_videos_returns_items():
    """hydrate_videos returns the items list from the videos.list response."""
    items = [{"id": "abc"}]
    client = _MockClient(videos_resp={"items": items})
    result = fetch.hydrate_videos(client, video_ids=["abc"])
    assert result == items


def test_hydrate_videos_raises_adapter_error_on_exception():
    """hydrate_videos wraps API exceptions in AdapterError."""

    class _FailingClient:
        def videos(self):
            raise RuntimeError("api error")

    with pytest.raises(AdapterError, match=r"youtube videos\.list failed"):
        fetch.hydrate_videos(_FailingClient(), video_ids=["x"])


def test_hydrate_channels_returns_items():
    """hydrate_channels returns the items list from the channels.list response."""
    items = [{"id": "UC123"}]
    client = _MockClient(channels_resp={"items": items})
    result = fetch.hydrate_channels(client, channel_ids=["UC123"])
    assert result == items


def test_hydrate_channels_raises_adapter_error_on_exception():
    """hydrate_channels wraps API exceptions in AdapterError."""

    class _FailingClient:
        def channels(self):
            raise RuntimeError("api error")

    with pytest.raises(AdapterError, match=r"youtube channels\.list failed"):
        fetch.hydrate_channels(_FailingClient(), channel_ids=["UC123"])
