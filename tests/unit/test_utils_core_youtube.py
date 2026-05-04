"""Tests for YouTube parsing helpers."""

from __future__ import annotations

from social_research_probe.utils.core.youtube import (
    youtube_video_id_from_item,
    youtube_video_id_from_url,
)


def test_youtube_video_id_from_url_watch_url():
    assert youtube_video_id_from_url("https://www.youtube.com/watch?v=abc123") == "abc123"


def test_youtube_video_id_from_url_short_url():
    assert youtube_video_id_from_url("https://youtu.be/xyz789") == "xyz789"


def test_youtube_video_id_from_url_non_string():
    assert youtube_video_id_from_url(None) is None


def test_youtube_video_id_from_url_without_id():
    assert youtube_video_id_from_url("https://www.youtube.com/channel/UC123") is None


def test_youtube_video_id_from_item_prefers_bare_id():
    item = {"id": "directid", "url": "https://www.youtube.com/watch?v=urlid"}
    assert youtube_video_id_from_item(item) == "directid"


def test_youtube_video_id_from_item_rejects_url_like_id():
    item = {"id": "https://example.com/watch?v=bad", "url": "https://youtu.be/good"}
    assert youtube_video_id_from_item(item) == "good"


def test_youtube_video_id_from_item_missing_id_and_url():
    assert youtube_video_id_from_item({"title": "No ID"}) is None
