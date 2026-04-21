"""Evidence tests — enrichment scaffolding produces deterministic strings + routing.

This phase tests the deterministic helpers in ``pipeline/enrichment.py`` —
prompt construction, fallback truncation, and the Jaccard-threshold routing
in ``_merge_or_pick``. LLM *semantic quality* is out of scope; Phase 10's
reliability harness covers that.

| Service | Input | Expected | Why |
| --- | --- | --- | --- |
| _build_summary_prompt | title, channel, transcript, word_limit=100 | contains title + channel + word_limit | structured prompt |
| _fallback_transcript_summary | 200-word transcript, word_limit=100 | 100 words + " ..." | truncation contract |
| _build_description_summary_prompt | ScoredItem with description | contains description verbatim | description fallback path |
| _merge_or_pick | text+url with Jaccard below threshold | returns text summary unchanged, never reconciles | threshold routing |
| _merge_or_pick | text+url with Jaccard above threshold + feature flag on | calls _reconcile_summaries | documented merge rule |
"""

from __future__ import annotations

from typing import ClassVar

import pytest

from social_research_probe.pipeline.enrichment import (
    _build_description_summary_prompt,
    _build_summary_prompt,
    _fallback_transcript_summary,
    _merge_or_pick,
)

# ---------------------------------------------------------------------------
# Prompt builders — deterministic string contracts
# ---------------------------------------------------------------------------


def test_build_summary_prompt_contains_title_channel_and_word_limit():
    prompt = _build_summary_prompt(
        title="How Attention Works",
        channel="Deep Learning Explained",
        transcript="[transcript body]",
        word_limit=150,
    )
    assert "150 words" in prompt
    assert "How Attention Works" in prompt
    assert "Deep Learning Explained" in prompt
    assert "[transcript body]" in prompt


def test_build_description_summary_prompt_contains_description_verbatim():
    item = {
        "title": "Test Title",
        "channel": "Test Channel",
        "published_at": "2026-01-15T00:00:00Z",
        "text_excerpt": "The video discusses recent advances in quantum error correction.",
    }
    prompt = _build_description_summary_prompt(item)
    assert "Test Title" in prompt
    assert "Test Channel" in prompt
    assert "quantum error correction" in prompt


# ---------------------------------------------------------------------------
# _fallback_transcript_summary — word-count truncation contract
# ---------------------------------------------------------------------------


def test_fallback_transcript_summary_truncates_to_word_limit():
    transcript = " ".join(f"w{i}" for i in range(200))
    result = _fallback_transcript_summary(transcript, word_limit=100)
    words = result.split()
    # Truncation appends " ..." marker which becomes one extra word.
    assert len(words) == 101
    assert words[-1] == "..."
    assert words[:5] == ["w0", "w1", "w2", "w3", "w4"]


def test_fallback_transcript_summary_returns_input_unchanged_when_shorter():
    short = " ".join(f"w{i}" for i in range(20))
    assert _fallback_transcript_summary(short, word_limit=100) == short


def test_fallback_transcript_summary_handles_empty_input():
    assert _fallback_transcript_summary("", word_limit=100) == ""


# ---------------------------------------------------------------------------
# _merge_or_pick — Jaccard-divergence routing
# ---------------------------------------------------------------------------


class _StubConfig:
    tunables: ClassVar[dict] = {}

    def feature_enabled(self, flag: str) -> bool:
        return True


@pytest.mark.anyio
async def test_merge_or_pick_below_threshold_returns_text_summary(monkeypatch):
    """Identical summaries have divergence 0.0 < any threshold → no reconcile call."""
    from social_research_probe.pipeline import enrichment as enrich

    calls: list[tuple] = []

    async def _spy_reconcile(**kwargs):  # pragma: no cover — assert below
        calls.append(kwargs)
        return "should not be called"

    monkeypatch.setattr(enrich, "_reconcile_summaries", _spy_reconcile)

    item: dict = {"title": "t", "channel": "c"}
    result = await _merge_or_pick(
        item,
        text_summary="identical summary text",
        url_summary="identical summary text",
        cleaned="transcript text",
        word_limit=100,
        divergence_threshold=0.4,
        cfg=_StubConfig(),
    )
    assert result == "identical summary text"
    assert calls == []  # Jaccard 0.0 below threshold 0.4 → no merge invocation


@pytest.mark.anyio
async def test_merge_or_pick_above_threshold_invokes_reconcile(monkeypatch):
    """Disjoint summaries have divergence 1.0 ≥ threshold → reconcile call is made."""
    from social_research_probe.pipeline import enrichment as enrich

    invocations: list[dict] = []

    async def _spy_reconcile(**kwargs):
        invocations.append(kwargs)
        return "[merged summary]"

    monkeypatch.setattr(enrich, "_reconcile_summaries", _spy_reconcile)

    item: dict = {"title": "Some Title", "channel": "Some Channel"}
    result = await _merge_or_pick(
        item,
        text_summary="alpha beta gamma",
        url_summary="delta epsilon zeta",
        cleaned="transcript text",
        word_limit=100,
        divergence_threshold=0.4,
        cfg=_StubConfig(),
    )
    assert result == "[merged summary]"
    assert len(invocations) == 1
    assert invocations[0]["transcript_summary"] == "alpha beta gamma"
    assert invocations[0]["url_summary"] == "delta epsilon zeta"


@pytest.mark.anyio
async def test_merge_or_pick_only_text_summary_returns_it_directly():
    item: dict = {"title": "t", "channel": "c"}
    result = await _merge_or_pick(
        item,
        text_summary="only text",
        url_summary=None,
        cleaned="",
        word_limit=100,
        divergence_threshold=0.4,
        cfg=_StubConfig(),
    )
    assert result == "only text"
