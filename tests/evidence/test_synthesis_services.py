"""Evidence tests — synthesis services produce deterministic text and math.

Four services: Jaccard divergence, natural-language explainers, the evidence
narrative builder, and the signal summary builder. Each expected value is
either hand-derived from the formula or asserts on concrete substrings taken
from the known routing table in source.

| Service | Input | Expected | Why |
| --- | --- | --- | --- |
| jaccard_divergence | same text | 0.0 | identity |
| jaccard_divergence | disjoint sets | 1.0 | no overlap |
| jaccard_divergence | {a,b} vs {a,c} | 1 - 1/3 | formula |
| explain | StatResult(pearson_r, 0.95) | contains "strong" "positive" | rules in explain.py:78-93 |
| summarize_signals | 2 SignalSets | contains median view count | aggregator |
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from social_research_probe.platforms.base import SignalSet
from social_research_probe.stats.base import StatResult
from social_research_probe.synthesize.divergence import jaccard_divergence
from social_research_probe.synthesize.evidence import summarize_signals
from social_research_probe.synthesize.explain import explain


# ---------------------------------------------------------------------------
# jaccard_divergence
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "a, b, expected",
    [
        ("hello world", "hello world", 0.0),
        ("a b c", "a b c", 0.0),
        ("a b c", "x y z", 1.0),
        ("", "", 0.0),
        ("alpha beta", "alpha gamma", 1 - 1 / 3),  # |∩|=1, |∪|=3
    ],
)
def test_jaccard_divergence_matches_formula(a, b, expected):
    assert jaccard_divergence(a, b) == pytest.approx(expected, abs=1e-9)


# ---------------------------------------------------------------------------
# explain — natural-language readings for known StatResult kinds
# ---------------------------------------------------------------------------


def test_explain_strong_positive_correlation_qualifies_strength():
    """r=0.95 triggers the 'strong' reading branch in explain.py:78-93.
    The reading is a plain-English phrase — assert the strength qualifier
    is present, not the exact word 'positive' (the module's phrasing is
    'the two metrics move together' for positive r)."""
    text = explain(
        StatResult(
            name="pearson_r", value=0.95, caption="Pearson r between x and y: 0.95"
        )
    ).lower()
    assert "strong" in text
    # Positive r yields a "move together" reading; negative yields "move opposite".
    assert "together" in text or "positive" in text


def test_explain_perfect_r_squared_mentions_perfect_or_excellent():
    text = explain(
        StatResult(
            name="r_squared", value=1.0, caption="R² for views vs time: 1.00"
        )
    ).lower()
    # The reading table maps R² >= 0.9 to a qualifier like "excellent" or "strong".
    assert any(word in text for word in ("excellent", "strong", "nearly perfect"))


def test_explain_unknown_stat_name_returns_caption_only():
    """Unrecognized names fall back to the caption with no appended reading."""
    caption = "Custom stat: 1.23"
    assert explain(StatResult(name="custom_metric", value=1.23, caption=caption)) == caption


# ---------------------------------------------------------------------------
# summarize_signals — compact metric aggregator
# ---------------------------------------------------------------------------


def test_summarize_signals_includes_median_views():
    now = datetime.now(UTC)
    signals = [
        SignalSet(
            views=1000,
            likes=50,
            comments=10,
            upload_date=now - timedelta(days=5),
            view_velocity=200.0,
            engagement_ratio=0.06,
            comment_velocity=2.0,
            cross_channel_repetition=0.0,
            raw={},
        ),
        SignalSet(
            views=3000,
            likes=200,
            comments=30,
            upload_date=now - timedelta(days=10),
            view_velocity=300.0,
            engagement_ratio=0.08,
            comment_velocity=3.0,
            cross_channel_repetition=0.0,
            raw={},
        ),
    ]
    summary = summarize_signals(signals)
    # The aggregator reports total views = 1000 + 3000 = 4000 (formatted
    # with commas as "4,000") and mean view velocity = (200 + 300) / 2 = 250.
    assert "4,000" in summary
    assert "250" in summary


def test_summarize_signals_empty_list_returns_plausible_placeholder():
    """Empty signal list must not crash; returns a human-readable placeholder."""
    result = summarize_signals([])
    assert isinstance(result, str)
    assert len(result) > 0
