"""Tests for YouTubeClient methods that require mocking the YouTube API client.

Covers search, _items_from_search, enrich, to_signals, and trust_hints using
mock fetch functions — no live API calls.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from social_research_probe.platforms.base import FetchLimits, RawItem
from social_research_probe.services.sourcing.youtube import YouTubeConnector, compute_engagement_metrics
from social_research_probe.utils.core.coerce import coerce_int as _as_int


def _make_connector(monkeypatch, api_key="test-key"):
    monkeypatch.setenv("SRP_YOUTUBE_API_KEY", api_key)
    return YouTubeConnector({"data_dir": None})


def _raw_item(
    vid_id="abc123",
    title="Test Video",
    channel_id="UC001",
    channel_title="Test Channel",
    published_at=None,
    views=1000,
    likes=50,
    comments=10,
    subscribers=5000,
):
    return RawItem(
        id=vid_id,
        url=f"https://www.youtube.com/watch?v={vid_id}",
        title=title,
        author_id=channel_id,
        author_name=channel_title,
        published_at=published_at or datetime(2024, 1, 1, tzinfo=UTC),
        metrics={"views": views, "likes": likes, "comments": comments},
        text_excerpt=None,
        thumbnail=None,
        extras={"channel_subscribers": subscribers, "duration_seconds": 300},
    )


# ---------------------------------------------------------------------------
# _items_from_search
# ---------------------------------------------------------------------------


def test_items_from_search_parses_raw(monkeypatch):
    """_items_from_search converts raw search result dicts into RawItem instances."""
    adapter = _make_connector(monkeypatch)
    raw = [
        {
            "id": {"videoId": "vid001"},
            "snippet": {
                "title": "My Video",
                "channelId": "UC999",
                "channelTitle": "My Channel",
                "publishedAt": "2024-03-01T12:00:00Z",
                "description": "A description",
                "thumbnails": {"default": {"url": "https://img.example.com/thumb.jpg"}},
            },
        }
    ]
    items = adapter._parse_search_results(raw)
    assert len(items) == 1
    item = items[0]
    assert item.id == "vid001"
    assert item.title == "My Video"
    assert item.author_id == "UC999"
    assert item.thumbnail == "https://img.example.com/thumb.jpg"
    assert item.text_excerpt == "A description"


def test_items_from_search_handles_bad_date(monkeypatch):
    """_items_from_search falls back to now() when publishedAt is unparseable."""
    adapter = _make_connector(monkeypatch)
    before = datetime.now(UTC)
    raw = [
        {
            "id": {"videoId": "v2"},
            "snippet": {"publishedAt": "not-a-date"},
        }
    ]
    items = adapter._parse_search_results(raw)
    assert len(items) == 1
    assert items[0].published_at >= before


def test_items_from_search_empty_raw(monkeypatch):
    """_items_from_search returns empty list for empty input."""
    adapter = _make_connector(monkeypatch)
    assert adapter._parse_search_results([]) == []


def test_as_int_handles_bool_float_and_bad_string():
    assert _as_int(True) == 1
    assert _as_int(4.9) == 4
    assert _as_int("oops") == 0


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------


def test_search_calls_fetch_and_parses(monkeypatch):
    """search() calls fetch._search_videos, returns RawItems."""
    import social_research_probe.technologies.media_fetch.youtube_api as fetch_mod

    fake_raw = [
        {
            "id": {"videoId": "s001"},
            "snippet": {
                "title": "Search Result",
                "channelId": "UC1",
                "channelTitle": "Chan",
                "publishedAt": "2024-01-01T00:00:00Z",
            },
        }
    ]
    monkeypatch.setattr(
        fetch_mod,
        "_search_videos",
        lambda api_key, topic, max_items, published_after: fake_raw,
    )
    adapter = _make_connector(monkeypatch)
    limits = FetchLimits(max_items=5, recency_days=30)
    items = adapter.find_by_topic("ai safety", limits)
    assert len(items) == 1
    assert items[0].id == "s001"


def test_client_is_rebuilt_per_call_to_avoid_stale_sockets(monkeypatch):
    """Each search builds a fresh client so httplib2 keep-alive sockets
    never go stale between calls (seen as SSL record-layer failures in prod)."""
    import social_research_probe.technologies.media_fetch.youtube_api as fetch_mod

    build_calls = [0]

    class _Exec:
        def execute(self):
            return {"items": []}

    class _Resource:
        def list(self, **_):
            return _Exec()

    class _FakeClient:
        def search(self):
            return _Resource()

    def _build(key):
        build_calls[0] += 1
        return _FakeClient()

    monkeypatch.setattr(fetch_mod, "_build_client", _build)

    adapter = _make_connector(monkeypatch)
    adapter.find_by_topic("topic", FetchLimits(max_items=1, recency_days=0))
    adapter.find_by_topic("topic-2", FetchLimits(max_items=1, recency_days=0))

    assert build_calls[0] == 2


def test_search_no_recency_days(monkeypatch):
    """search() passes published_after=None when recency_days is None."""
    import social_research_probe.technologies.media_fetch.youtube_api as fetch_mod

    captured = {}
    monkeypatch.setattr(
        fetch_mod,
        "_search_videos",
        lambda api_key, topic, max_items, published_after: (
            captured.update({"pa": published_after}) or []
        ),
    )
    adapter = _make_connector(monkeypatch)
    adapter.find_by_topic("ai", FetchLimits(max_items=5, recency_days=None))
    assert captured["pa"] is None


# ---------------------------------------------------------------------------
# enrich
# ---------------------------------------------------------------------------


async def test_enrich_empty_returns_empty(monkeypatch):
    """enrich() returns empty list unchanged when given no items."""
    adapter = _make_connector(monkeypatch)
    assert await adapter.fetch_item_details([]) == []


async def test_enrich_hydrates_items(monkeypatch):
    """enrich() merges video and channel stats into RawItem metrics."""
    import social_research_probe.technologies.media_fetch.youtube_api as fetch_mod

    monkeypatch.setattr(
        fetch_mod,
        "_fetch_video_details",
        lambda api_key, video_ids: [
            {
                "id": "abc123",
                "statistics": {
                    "viewCount": "2000",
                    "likeCount": "100",
                    "commentCount": "20",
                },
                "contentDetails": {"duration": "PT5M30S"},
            }
        ],
    )
    monkeypatch.setattr(
        fetch_mod,
        "_fetch_channel_details",
        lambda api_key, channel_ids: [
            {
                "id": "UC001",
                "statistics": {"subscriberCount": "10000", "videoCount": "50"},
            }
        ],
    )
    adapter = _make_connector(monkeypatch)
    items = [_raw_item()]
    enriched = await adapter.fetch_item_details(items)
    assert len(enriched) == 1
    assert enriched[0].metrics["views"] == 2000
    assert enriched[0].metrics["likes"] == 100
    assert enriched[0].extras["channel_subscribers"] == 10000


async def test_enrich_no_duration_string(monkeypatch):
    """enrich() handles items with no contentDetails.duration gracefully."""
    import social_research_probe.technologies.media_fetch.youtube_api as fetch_mod

    monkeypatch.setattr(
        fetch_mod,
        "_fetch_video_details",
        lambda api_key, video_ids: [
            {
                "id": "abc123",
                "statistics": {
                    "viewCount": "300",
                    "likeCount": "10",
                    "commentCount": "2",
                },
                "contentDetails": {"duration": ""},
            }
        ],
    )
    monkeypatch.setattr(
        fetch_mod,
        "_fetch_channel_details",
        lambda api_key, channel_ids: [],
    )
    adapter = _make_connector(monkeypatch)
    items = [_raw_item()]
    enriched = await adapter.fetch_item_details(items)
    assert len(enriched) == 1
    assert enriched[0].metrics["views"] == 300


async def test_enrich_includes_shorts_by_default(monkeypatch):
    """enrich() now keeps YouTube Shorts by default and tags them in extras."""
    import social_research_probe.technologies.media_fetch.youtube_api as fetch_mod

    monkeypatch.setattr(
        fetch_mod,
        "_fetch_video_details",
        lambda api_key, video_ids: [
            {
                "id": "abc123",
                "statistics": {
                    "viewCount": "500",
                    "likeCount": "5",
                    "commentCount": "1",
                },
                "contentDetails": {"duration": "PT45S"},
            }
        ],
    )
    monkeypatch.setattr(fetch_mod, "_fetch_channel_details", lambda api_key, channel_ids: [])
    adapter = _make_connector(monkeypatch)
    enriched = await adapter.fetch_item_details([_raw_item()])
    assert len(enriched) == 1
    assert enriched[0].extras["is_short"] is True


async def test_enrich_skips_shorts_when_include_shorts_false(monkeypatch):
    """When config has include_shorts=False, Shorts are filtered out."""
    import social_research_probe.technologies.media_fetch.youtube_api as fetch_mod

    monkeypatch.setattr(
        fetch_mod,
        "_fetch_video_details",
        lambda api_key, video_ids: [
            {
                "id": "abc123",
                "statistics": {
                    "viewCount": "500",
                    "likeCount": "5",
                    "commentCount": "1",
                },
                "contentDetails": {"duration": "PT45S"},
            }
        ],
    )
    monkeypatch.setattr(fetch_mod, "_fetch_channel_details", lambda api_key, channel_ids: [])
    adapter = _make_connector(monkeypatch)
    adapter.config["include_shorts"] = False
    assert await adapter.fetch_item_details([_raw_item()]) == []


# ---------------------------------------------------------------------------
# to_signals
# ---------------------------------------------------------------------------


def test_to_signals_computes_velocity(monkeypatch):
    """to_signals() computes view_velocity and engagement_ratio from metrics."""
    adapter = _make_connector(monkeypatch)
    published = datetime.now(UTC) - timedelta(days=10)
    item = _raw_item(views=1000, likes=50, comments=10, published_at=published)
    engagement_metrics = compute_engagement_metrics([item])
    assert len(engagement_metrics) == 1
    sig = engagement_metrics[0]
    assert sig.views == 1000
    assert sig.view_velocity == pytest.approx(100.0)
    assert sig.engagement_ratio == pytest.approx(60 / 1000)


def test_to_signals_empty(monkeypatch):
    """to_signals() returns empty list for empty input."""
    adapter = _make_connector(monkeypatch)
    assert compute_engagement_metrics([]) == []


