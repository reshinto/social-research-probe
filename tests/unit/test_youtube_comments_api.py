"""Tests for fetch_youtube_comments() in technologies/media_fetch/youtube_api.py."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from social_research_probe.technologies.media_fetch import youtube_api


def _make_client(items):
    client = MagicMock()
    (client.commentThreads.return_value.list.return_value.execute.return_value) = {"items": items}
    return client


def test_fetch_calls_comment_threads_list():
    client = _make_client([{"snippet": {}}])
    with (
        patch.object(youtube_api, "resolve_youtube_api_key", return_value="key"),
        patch.object(youtube_api, "_build_client", return_value=client),
    ):
        youtube_api.fetch_youtube_comments("vid1", max_results=10, order="time")

    client.commentThreads.return_value.list.assert_called_once_with(
        videoId="vid1",
        part="snippet",
        maxResults=10,
        textFormat="plainText",
        order="time",
    )


def test_fetch_returns_dict_items():
    items = [{"snippet": {"a": 1}}, {"snippet": {"b": 2}}]
    client = _make_client(items)
    with (
        patch.object(youtube_api, "resolve_youtube_api_key", return_value="key"),
        patch.object(youtube_api, "_build_client", return_value=client),
    ):
        result = youtube_api.fetch_youtube_comments("vid1")

    assert result == items


def test_fetch_empty_response_returns_empty_list():
    client = _make_client([])
    with (
        patch.object(youtube_api, "resolve_youtube_api_key", return_value="key"),
        patch.object(youtube_api, "_build_client", return_value=client),
    ):
        result = youtube_api.fetch_youtube_comments("vid1")

    assert result == []


def test_fetch_missing_items_key_returns_empty_list():
    client = MagicMock()
    client.commentThreads.return_value.list.return_value.execute.return_value = {}
    with (
        patch.object(youtube_api, "resolve_youtube_api_key", return_value="key"),
        patch.object(youtube_api, "_build_client", return_value=client),
    ):
        result = youtube_api.fetch_youtube_comments("vid1")

    assert result == []


def test_fetch_filters_non_dict_items():
    client = _make_client([{"snippet": {}}, "not-a-dict", 42, None])
    with (
        patch.object(youtube_api, "resolve_youtube_api_key", return_value="key"),
        patch.object(youtube_api, "_build_client", return_value=client),
    ):
        result = youtube_api.fetch_youtube_comments("vid1")

    assert result == [{"snippet": {}}]


def test_fetch_uses_resolve_api_key_and_build_client():
    client = _make_client([])
    with (
        patch.object(youtube_api, "resolve_youtube_api_key", return_value="mykey") as rk,
        patch.object(youtube_api, "_build_client", return_value=client) as bc,
    ):
        youtube_api.fetch_youtube_comments("vid1")

    rk.assert_called_once()
    bc.assert_called_once_with("mykey")


def test_fetch_propagates_api_error():
    client = MagicMock()
    client.commentThreads.return_value.list.return_value.execute.side_effect = RuntimeError(
        "quota exceeded"
    )
    with (
        patch.object(youtube_api, "resolve_youtube_api_key", return_value="key"),
        patch.object(youtube_api, "_build_client", return_value=client),
    ):
        with pytest.raises(RuntimeError, match="quota exceeded"):
            youtube_api.fetch_youtube_comments("vid1")


def test_fetch_comment_threads_non_list_items_returns_empty():
    client = MagicMock()
    client.commentThreads.return_value.list.return_value.execute.return_value = {
        "items": "unexpected-string"
    }
    with (
        patch.object(youtube_api, "resolve_youtube_api_key", return_value="key"),
        patch.object(youtube_api, "_build_client", return_value=client),
    ):
        result = youtube_api.fetch_youtube_comments("vid1")

    assert result == []
