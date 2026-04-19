"""Platform adapter dataclasses + ABC contract."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from social_research_probe.platforms.base import (
    FetchLimits,
    PlatformAdapter,
    RawItem,
    SignalSet,
    TrustHints,
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
    sig = SignalSet(
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


def test_trust_hints_defaults_allow_nones():
    hints = TrustHints(
        account_age_days=None,
        verified=None,
        subscriber_count=None,
        upload_cadence_days=None,
        citation_markers=[],
    )
    assert hints.citation_markers == []


def test_adapter_is_abstract():
    with pytest.raises(TypeError):
        PlatformAdapter()


def test_fetch_text_for_claim_extraction_returns_none():
    """Line 75: default fetch_text_for_claim_extraction returns None."""
    from datetime import datetime

    from social_research_probe.platforms.base import (
        FetchLimits,
        PlatformAdapter,
        RawItem,
        TrustHints,
    )

    class ConcreteAdapter(PlatformAdapter):
        name = "test"
        default_limits = FetchLimits()

        def health_check(self) -> bool:
            return True

        def search(self, topic, limits):
            return []

        def enrich(self, items):
            return items

        def to_signals(self, items):
            return []

        def trust_hints(self, item):
            return TrustHints(None, None, None, None, [])

        def url_normalize(self, url):
            return url

    adapter = ConcreteAdapter()
    item = RawItem(
        id="x",
        url="https://example.com",
        title="T",
        author_id="a",
        author_name="Author",
        published_at=datetime.now(UTC),
        metrics={},
        text_excerpt=None,
        thumbnail=None,
        extras={},
    )
    result = adapter.fetch_text_for_claim_extraction(item)
    assert result is None
