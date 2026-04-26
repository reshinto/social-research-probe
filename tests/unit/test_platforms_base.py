"""Tests for platforms/base.py contracts and domain types."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from social_research_probe.platforms.base import (
    EngagementMetrics,
    FetchClient,
    FetchLimits,
    PlatformClient,
    RawItem,
    SearchClient,
)


def test_fetch_limits_defaults():
    limits = FetchLimits()
    assert limits.max_items == 20
    assert limits.recency_days == 90


def test_fetch_limits_is_frozen():
    limits = FetchLimits()
    with pytest.raises(AttributeError):
        limits.max_items = 5


def test_raw_item_required_fields():
    item = RawItem(
        id="v1",
        url="https://example/v1",
        title="T",
        author_id="c1",
        author_name="Channel",
        published_at=datetime.now(UTC),
        metrics={"views": 100},
        text_excerpt=None,
        thumbnail=None,
        extras={},
    )
    assert item.id == "v1"


def test_signal_set_allows_none_metrics():
    sig = EngagementMetrics(
        views=None,
        likes=None,
        comments=None,
        upload_date=None,
        view_velocity=None,
        engagement_ratio=None,
        comment_velocity=None,
        cross_channel_repetition=None,
        raw={},
    )
    assert sig.views is None


def test_platform_client_is_abstract():
    with pytest.raises(TypeError):
        PlatformClient()  # type: ignore[abstract]


def test_search_client_is_abstract():
    with pytest.raises(TypeError):
        SearchClient()  # type: ignore[abstract]


def test_fetch_client_is_abstract():
    with pytest.raises(TypeError):
        FetchClient()  # type: ignore[abstract]


def test_search_client_is_platform_client():
    class ConcreteSearch(SearchClient):
        name = "test"
        default_limits = FetchLimits()

        def health_check(self) -> bool:
            return True

        def search(self, topic, limits):
            return []

        async def enrich(self, items):
            return items

    assert issubclass(ConcreteSearch, PlatformClient)


def test_fetch_client_is_platform_client():
    class ConcreteFetch(FetchClient):
        name = "test"

        def health_check(self) -> bool:
            return True

        async def fetch(self, url):
            return []

    assert issubclass(ConcreteFetch, PlatformClient)
