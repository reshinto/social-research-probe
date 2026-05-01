"""Tests for YouTubeCommentsTech in technologies/media_fetch/__init__.py."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

from social_research_probe.technologies.media_fetch import YouTubeCommentsTech


def _raw_thread(
    comment_id="c1", author="Alice", text="Nice", like_count=5, published_at="2026-01-01T00:00:00Z"
):
    return {
        "snippet": {
            "topLevelComment": {
                "id": comment_id,
                "snippet": {
                    "authorDisplayName": author,
                    "textDisplay": text,
                    "likeCount": like_count,
                    "publishedAt": published_at,
                },
            }
        }
    }


def _run(coro):
    return asyncio.run(coro)


def _enabled_cfg():
    cfg = MagicMock()
    cfg.technology_enabled.return_value = True
    cfg.debug_enabled.return_value = False
    return cfg


def _disabled_cfg():
    cfg = MagicMock()
    cfg.technology_enabled.return_value = False
    return cfg


def test_name():
    assert YouTubeCommentsTech.name == "youtube_comments"


def test_enabled_config_key():
    assert YouTubeCommentsTech.enabled_config_key == "youtube_comments"


def test_execute_returns_source_comments():
    raw = [_raw_thread("c1", "Alice", "Great!", 10, "2026-01-01T00:00:00Z")]
    with (
        patch(
            "social_research_probe.technologies.media_fetch.youtube_api.fetch_youtube_comments",
            return_value=raw,
        ),
        patch("social_research_probe.technologies.load_active_config", return_value=_enabled_cfg()),
    ):
        result = _run(YouTubeCommentsTech().execute(("vid1", 20, "relevance")))

    assert result is not None
    assert len(result) == 1
    assert result[0]["comment_id"] == "c1"


def test_execute_extracts_all_fields():
    raw = [_raw_thread("c42", "Bob", "Hello world", 7, "2026-03-15T12:00:00Z")]
    with (
        patch(
            "social_research_probe.technologies.media_fetch.youtube_api.fetch_youtube_comments",
            return_value=raw,
        ),
        patch("social_research_probe.technologies.load_active_config", return_value=_enabled_cfg()),
    ):
        result = _run(YouTubeCommentsTech().execute(("vid2", 20, "relevance")))

    assert result is not None
    c = result[0]
    assert c["comment_id"] == "c42"
    assert c["author"] == "Bob"
    assert c["text"] == "Hello world"
    assert c["like_count"] == 7
    assert c["published_at"] == "2026-03-15T12:00:00Z"
    assert c["platform"] == "youtube"
    assert c["source_id"] == "vid2"


def test_execute_empty_raw_returns_empty_list():
    with (
        patch(
            "social_research_probe.technologies.media_fetch.youtube_api.fetch_youtube_comments",
            return_value=[],
        ),
        patch("social_research_probe.technologies.load_active_config", return_value=_enabled_cfg()),
    ):
        result = _run(YouTubeCommentsTech().execute(("vid1", 20, "relevance")))

    assert result == []


def test_execute_skips_malformed_items():
    raw = [
        "not-a-dict",
        {"snippet": None},
        {"snippet": {"topLevelComment": None}},
        {"snippet": {"topLevelComment": {"snippet": None}}},
        {"snippet": {"topLevelComment": {"id": None, "snippet": {"textDisplay": "x"}}}},
        _raw_thread("c1"),
    ]
    with (
        patch(
            "social_research_probe.technologies.media_fetch.youtube_api.fetch_youtube_comments",
            return_value=raw,
        ),
        patch("social_research_probe.technologies.load_active_config", return_value=_enabled_cfg()),
    ):
        result = _run(YouTubeCommentsTech().execute(("vid1", 20, "relevance")))

    assert result is not None
    assert len(result) == 1
    assert result[0]["comment_id"] == "c1"


def test_disabled_returns_none():
    with patch(
        "social_research_probe.technologies.load_active_config", return_value=_disabled_cfg()
    ):
        result = _run(YouTubeCommentsTech().execute(("vid1", 20, "relevance")))

    assert result is None


def test_api_exception_returns_none():
    cfg = _enabled_cfg()
    with (
        patch(
            "social_research_probe.technologies.media_fetch.youtube_api.fetch_youtube_comments",
            side_effect=RuntimeError("quota exceeded"),
        ),
        patch("social_research_probe.technologies.load_active_config", return_value=cfg),
    ):
        result = _run(YouTubeCommentsTech().execute(("vid1", 20, "relevance")))

    assert result is None
