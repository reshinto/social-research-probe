"""Tests for the evidence aggregator covering all summarisation branches."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from social_research_probe.synthesize.evidence import summarize, summarize_engagement_metrics

from social_research_probe.platforms.base import EngagementMetrics, RawItem


def _item(channel: str = "ch", title: str = "t") -> RawItem:
    return RawItem(
        id="x",
        url="https://example.com",
        title=title,
        author_id="a",
        author_name=channel,
        published_at=datetime.now(UTC),
        metrics={"views": 1000, "likes": 10, "comments": 1},
        text_excerpt="",
        thumbnail=None,
        extras={},
    )


def _signal(
    *,
    upload_date: datetime | None = None,
    velocity: float | None = 100.0,
    engagement: float | None = 0.05,
    views: int = 1000,
) -> EngagementMetrics:
    return EngagementMetrics(
        views=views,
        likes=10,
        comments=1,
        upload_date=upload_date,
        view_velocity=velocity,
        engagement_ratio=engagement,
        comment_velocity=0.0,
        cross_channel_repetition=0.0,
        raw={},
    )


class TestSummarize:
    def test_empty_items_returns_placeholder(self):
        assert summarize([], [], []) == "no items fetched"

    def test_full_summary_with_all_signals(self):
        now = datetime(2026, 4, 19, tzinfo=UTC)
        items = [_item("ch1"), _item("ch2"), _item("ch1")]
        engagement_metrics = [
            _signal(upload_date=now - timedelta(days=2)),
            _signal(upload_date=now - timedelta(days=4)),
            _signal(upload_date=now - timedelta(days=6)),
        ]
        top_n = [{"source_class": "primary"}, {"source_class": "secondary"}]
        result = summarize(items, engagement_metrics, top_n, now=now)
        assert "3 items from 2 channels" in result
        assert "median upload age 4d" in result
        assert "avg view velocity 100/day" in result
        assert "avg engagement 0.050" in result
        assert "top-N source mix:" in result

    def test_no_upload_dates_omits_age(self):
        items = [_item()]
        engagement_metrics = [_signal(upload_date=None)]
        result = summarize(items, engagement_metrics, [])
        assert "median upload age" not in result

    def test_no_velocity_omits_it(self):
        items = [_item()]
        engagement_metrics = [_signal(velocity=None, engagement=None)]
        result = summarize(items, engagement_metrics, [])
        assert "avg view velocity" not in result
        assert "avg engagement" not in result

    def test_empty_top_n_omits_mix(self):
        items = [_item()]
        engagement_metrics = [_signal()]
        result = summarize(items, engagement_metrics, [])
        assert "source mix" not in result

    def test_default_now_when_none(self):
        items = [_item()]
        engagement_metrics = [_signal(upload_date=datetime.now(UTC) - timedelta(days=1))]
        result = summarize(items, engagement_metrics, [])
        assert "median upload age" in result


class TestSummarizeSignals:
    def test_empty_signals_returns_placeholder(self):
        assert summarize_engagement_metrics([]) == "no data"

    def test_full_metric_summary(self):
        engagement_metrics = [
            _signal(views=1000, velocity=50.0),
            _signal(views=2000, velocity=150.0),
        ]
        result = summarize_engagement_metrics(engagement_metrics)
        assert "2 items" in result
        assert "total views: 3,000" in result
        assert "view velocity mean=100/day max=150/day" in result
        assert "engagement ratio mean=0.050" in result

    def test_no_velocity_omits_velocity_section(self):
        engagement_metrics = [_signal(velocity=None, engagement=None)]
        result = summarize_engagement_metrics(engagement_metrics)
        assert "view velocity" not in result
        assert "engagement ratio" not in result
