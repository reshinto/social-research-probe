"""Tests for services.sourcing.youtube."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from social_research_probe.platforms.base import RawItem
from social_research_probe.services.sourcing.youtube import (
    YouTubeConnector,
    _recency_cutoff,
    compute_engagement_metrics,
)


def test_recency_cutoff_none():
    assert _recency_cutoff(None) is None
    assert _recency_cutoff(0) is None


def test_recency_cutoff_format():
    out = _recency_cutoff(7)
    assert out and "T" in out and out.endswith("Z")


def test_compute_engagement_metrics_empty():
    assert compute_engagement_metrics([]) == []


def test_compute_engagement_metrics_basic():
    item = RawItem(
        id="1",
        url="u",
        title="t",
        author_id="a",
        author_name="A",
        published_at=datetime.now(UTC) - timedelta(days=10),
        metrics={"views": 1000, "likes": 50, "comments": 10},
        text_excerpt=None,
        thumbnail=None,
        extras={},
    )
    out = compute_engagement_metrics([item])
    assert len(out) == 1
    em = out[0]
    assert em.views == 1000
    assert em.view_velocity == 100.0
    assert em.engagement_ratio == 60 / 1000


def test_youtube_connector_parse_search_basic():
    raw = [
        {
            "id": {"videoId": "vid1"},
            "snippet": {
                "publishedAt": "2025-01-01T00:00:00Z",
                "title": "T1",
                "channelId": "c1",
                "channelTitle": "Chan",
                "description": "d",
                "thumbnails": {"default": {"url": "https://thumb"}},
            },
        }
    ]
    conn = YouTubeConnector.__new__(YouTubeConnector)
    conn.config = {}
    items = conn._parse_search_results(raw)
    assert len(items) == 1
    assert items[0].url == "https://www.youtube.com/watch?v=vid1"
    assert items[0].title == "T1"


def test_youtube_connector_parse_search_invalid_date():
    raw = [{"id": {"videoId": "v"}, "snippet": {"publishedAt": "garbage"}}]
    conn = YouTubeConnector.__new__(YouTubeConnector)
    conn.config = {}
    items = conn._parse_search_results(raw)
    assert items[0].id == "v"


def test_youtube_connector_filter_shorts_kept_when_enabled():
    conn = YouTubeConnector.__new__(YouTubeConnector)
    conn.config = {"include_shorts": True}
    item = RawItem(
        id="1",
        url="",
        title="",
        author_id="",
        author_name="",
        published_at=datetime.now(UTC),
        metrics={},
        text_excerpt=None,
        thumbnail=None,
        extras={"is_short": True},
    )
    out = conn._filter_shorts([item])
    assert len(out) == 1


def test_youtube_connector_filter_shorts_dropped_when_disabled():
    conn = YouTubeConnector.__new__(YouTubeConnector)
    conn.config = {"include_shorts": False}
    item = RawItem(
        id="1",
        url="",
        title="",
        author_id="",
        author_name="",
        published_at=datetime.now(UTC),
        metrics={},
        text_excerpt=None,
        thumbnail=None,
        extras={"is_short": True},
    )
    assert conn._filter_shorts([item]) == []
