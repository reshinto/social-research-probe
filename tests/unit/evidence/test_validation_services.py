"""Evidence tests — validation services classify sources and detect AI slop.

Two services: the source classifier (PRIMARY / SECONDARY / COMMENTARY /
UNKNOWN routing) and the AI-slop detector (heuristic score in [0, 1]).

| Service | Input | Expected | Why |
| --- | --- | --- | --- |
| classify | verified + 5y old + 200k subs | PRIMARY | rule in source.py:30-42 |
| classify | no markers + <180d + <5k subs | COMMENTARY | documented rule |
| classify | has arxiv citation + 5y old + unverified | SECONDARY (not verified) | verified required for PRIMARY |
| classify | no signals | UNKNOWN | fallthrough |
| ai_slop.score | lots of boilerplate phrases | high score | _boilerplate_signal |
| ai_slop.score | unique natural prose | low score | diverse trigrams |
| ai_slop.score | "" | 0.0 | early return |
"""

from __future__ import annotations

from datetime import UTC, datetime

from social_research_probe.platforms.base import RawItem, TrustHints
from social_research_probe.validation.ai_slop import score as slop_score
from social_research_probe.validation.source import SourceClass, classify


def _item(title: str = "t") -> RawItem:
    return RawItem(
        id="x",
        url="https://example.com",
        title=title,
        author_id="c",
        author_name="creator",
        published_at=datetime.now(UTC),
        metrics={},
        text_excerpt=None,
        thumbnail=None,
        extras={},
    )


# ---------------------------------------------------------------------------
# Source classification
# ---------------------------------------------------------------------------


def test_classify_verified_long_lived_large_channel_is_primary():
    hints = TrustHints(
        account_age_days=2000,
        verified=True,
        subscriber_count=200_000,
        upload_cadence_days=7.0,
        citation_markers=[],
    )
    assert classify(_item(), hints) == SourceClass.PRIMARY


def test_classify_young_channel_with_no_citations_is_commentary():
    hints = TrustHints(
        account_age_days=30,
        verified=False,
        subscriber_count=100,
        upload_cadence_days=None,
        citation_markers=[],
    )
    assert classify(_item(), hints) == SourceClass.COMMENTARY


def test_classify_arxiv_citation_without_verification_stays_secondary():
    """Primary requires verified=True; arxiv citation alone downgrades to SECONDARY."""
    hints = TrustHints(
        account_age_days=2000,
        verified=False,
        subscriber_count=10_000,
        upload_cadence_days=14.0,
        citation_markers=["https://arxiv.org/abs/2401.12345"],
    )
    assert classify(_item(), hints) == SourceClass.SECONDARY


def test_classify_missing_signals_falls_through_to_unknown():
    """Old enough to escape COMMENTARY, no citations, low subscribers → UNKNOWN."""
    hints = TrustHints(
        account_age_days=365,  # not <180 so not COMMENTARY
        verified=False,
        subscriber_count=500,  # below 1000 SECONDARY threshold
        upload_cadence_days=None,
        citation_markers=[],
    )
    assert classify(_item(), hints) == SourceClass.UNKNOWN


# ---------------------------------------------------------------------------
# AI-slop detector — boilerplate-heavy vs natural prose
# ---------------------------------------------------------------------------


def test_ai_slop_returns_zero_for_empty_string():
    assert slop_score("") == 0.0


def test_ai_slop_rates_heavy_boilerplate_higher_than_natural_prose():
    """Text with known boilerplate phrases must score strictly higher than
    a roughly-equal-length paragraph of natural prose."""
    slop_text = (
        "In today's video, we will explore the fascinating world of artificial intelligence. "
        "As we will see, this is a game-changing technology. Stay tuned for more. "
        "Don't forget to like and subscribe. In conclusion, AI is revolutionary."
    )
    natural_text = (
        "Transformers introduced attention-based sequence modelling that replaced recurrent "
        "architectures for most language tasks. Their parallel self-attention lets gradients "
        "flow across very long contexts, enabling much larger training corpora. Empirically "
        "this produced the first broadly usable text generators."
    )
    slop = slop_score(slop_text)
    natural = slop_score(natural_text)
    assert slop > natural
    assert 0.0 <= natural <= 1.0
    assert 0.0 <= slop <= 1.0
