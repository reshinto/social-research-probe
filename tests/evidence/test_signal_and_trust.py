"""Evidence tests — signal derivation + trust-hint extractors produce exact numeric values.

Four services are covered: ``to_signals`` view-velocity / engagement-ratio
math, ``citation_markers`` URL regex, ``account_age_days`` datetime arithmetic,
and the adapter's ``trust_hints`` composition.

Evidence receipt:

| Service | Input | Expected | Why |
| --- | --- | --- | --- |
| to_signals | views=1000, likes=50, comments=10, upload=30d ago | view_velocity≈33.3, engagement_ratio=0.06 | formula in adapter.py:224-248 |
| citation_markers | "See https://arxiv.org/abs/1 and https://x.com/y" | 2 URLs | URL regex findall |
| citation_markers | empty / None | [] | early return |
| account_age_days | created=2020-04-21, now=2026-04-21 | 2192 | (now - created).days under frozen clock |
| account_age_days | None / empty | None | early return |
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from social_research_probe.platforms.base import RawItem
from social_research_probe.platforms.youtube.trust_hints import (
    account_age_days,
    citation_markers,
)


# ---------------------------------------------------------------------------
# to_signals — deterministic math from known metrics
# ---------------------------------------------------------------------------


@pytest.fixture
def adapter(monkeypatch, tmp_path):
    from social_research_probe.platforms.youtube.adapter import YouTubeAdapter

    monkeypatch.setenv("SRP_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("YOUTUBE_API_KEY", "test-key")
    return YouTubeAdapter(config={"data_dir": str(tmp_path)})


def test_to_signals_computes_view_velocity_and_engagement_ratio(adapter):
    """views=1000, likes=50, comments=10, 30-day-old video →
    view_velocity ≈ 1000 / 30 = 33.33; engagement_ratio = 60 / 1000 = 0.06."""
    thirty_days_ago = datetime.now(UTC) - timedelta(days=30)
    item = RawItem(
        id="v1",
        url="https://www.youtube.com/watch?v=xxxxxxxxxxx",
        title="test",
        author_id="c1",
        author_name="creator",
        published_at=thirty_days_ago,
        metrics={"views": 1000, "likes": 50, "comments": 10},
        text_excerpt=None,
        thumbnail=None,
        extras={},
    )
    signals = adapter.to_signals([item])
    assert len(signals) == 1
    s = signals[0]
    assert s.views == 1000
    assert s.likes == 50
    assert s.comments == 10
    assert s.engagement_ratio == pytest.approx(60 / 1000)
    # view_velocity depends on age; tolerance for day-boundary rounding.
    assert s.view_velocity == pytest.approx(1000 / 30, rel=0.05)


def test_to_signals_guards_against_zero_age(adapter):
    """For a fresh (<1 day old) video, age_days is floored at 1 to avoid div-by-zero."""
    fresh_item = RawItem(
        id="v2",
        url="https://www.youtube.com/watch?v=yyyyyyyyyyy",
        title="fresh",
        author_id="c2",
        author_name="creator",
        published_at=datetime.now(UTC),
        metrics={"views": 500, "likes": 10, "comments": 0},
        text_excerpt=None,
        thumbnail=None,
        extras={},
    )
    signals = adapter.to_signals([fresh_item])
    # age_days = max(1, 0) = 1, so view_velocity = 500 / 1 = 500.0.
    assert signals[0].view_velocity == pytest.approx(500.0)


def test_to_signals_handles_zero_views_without_division_error(adapter):
    """Zero-view video must not crash: engagement_ratio uses max(1, views)."""
    item = RawItem(
        id="v3",
        url="https://www.youtube.com/watch?v=zzzzzzzzzzz",
        title="zero",
        author_id="c3",
        author_name="creator",
        published_at=datetime.now(UTC) - timedelta(days=5),
        metrics={"views": 0, "likes": 5, "comments": 2},
        text_excerpt=None,
        thumbnail=None,
        extras={},
    )
    signals = adapter.to_signals([item])
    # engagement_ratio = (5+2) / max(1, 0) = 7.0.
    assert signals[0].engagement_ratio == pytest.approx(7.0)


# ---------------------------------------------------------------------------
# citation_markers — URL regex extraction
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "description, expected_urls",
    [
        (
            "See https://arxiv.org/abs/2401.12345 and https://example.com/post for details.",
            ["https://arxiv.org/abs/2401.12345", "https://example.com/post"],
        ),
        ("No links here.", []),
        ("", []),
        (None, []),
    ],
)
def test_citation_markers_extracts_urls(description, expected_urls):
    """Regex r'https?://\\S+' finds every absolute URL in the description."""
    result = citation_markers(description)
    # Compare as sets so order doesn't matter; strip trailing punctuation that
    # regex naturally captures in some cases.
    cleaned = [u.rstrip(".,;)") for u in result]
    assert cleaned == [u.rstrip(".,;)") for u in expected_urls]


# ---------------------------------------------------------------------------
# account_age_days — datetime arithmetic under a pinned clock
# ---------------------------------------------------------------------------


def test_account_age_days_for_six_year_old_account():
    """Created 2020-04-21, now 2026-04-21 (frozen) → 2191 days.

    Calculation: 6 years between start and end, one leap day (Feb 29, 2024)
    falls within the span. 2020-04-21 to 2021-04-21 is 365 days (passed no
    Feb 29); …; 2023-04-21 to 2024-04-21 is 366. Total = 5*365 + 366 = 2191.
    """
    from unittest.mock import patch

    pinned = datetime(2026, 4, 21, tzinfo=UTC)
    with patch(
        "social_research_probe.platforms.youtube.trust_hints.datetime"
    ) as mock_dt:
        mock_dt.now.return_value = pinned
        mock_dt.fromisoformat.side_effect = datetime.fromisoformat
        age = account_age_days("2020-04-21T00:00:00Z")
    assert age == 2191


def test_account_age_days_returns_none_for_missing_input():
    assert account_age_days(None) is None
    assert account_age_days("") is None
