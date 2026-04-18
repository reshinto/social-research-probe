"""Platform adapter dataclasses + ABC contract."""
from __future__ import annotations

from datetime import datetime, timezone

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
    with pytest.raises(Exception):
        limits.max_items = 5  # type: ignore[misc]


def test_raw_item_required_fields():
    item = RawItem(
        id="v1",
        url="https://example/v1",
        title="T",
        author_id="c1",
        author_name="Channel",
        published_at=datetime.now(timezone.utc),
        metrics={"views": 100},
        text_excerpt=None,
        thumbnail=None,
        extras={},
    )
    assert item.id == "v1"


def test_signal_set_allows_none_metrics():
    sig = SignalSet(
        views=None, likes=None, comments=None,
        upload_date=None,
        view_velocity=None, engagement_ratio=None,
        comment_velocity=None, cross_channel_repetition=None,
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
        PlatformAdapter()  # type: ignore[abstract]
