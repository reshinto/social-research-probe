"""Evidence tests — summary-quality scaffolding (deterministic, CI-safe).

Phase 9 of the evidence-suite plan ships the **deterministic** coverage-logic
test. Non-deterministic LLM variance is Phase 10's job (reliability harness).

The test uses a canned summary (no real LLM call) to verify:

1. ``coverage_score`` returns the correct fraction of required keyphrases.
2. ``hallucinated_proper_nouns`` detects capitalized tokens not in the
   transcript or allowed list.
3. ``_fallback_transcript_summary`` now truncates at sentence boundaries
   rather than cutting mid-word.
4. The redesigned ``_build_summary_prompt`` embeds the anti-hallucination
   rule, filler blocklist guidance, and the one-shot exemplar.

Observed pre-redesign failure modes in cached summaries (captured here so
Phase 11 can cite them in ``docs/summary-quality-report.md``):

- Generic filler ("This video discusses…", "Overall,…")
- Missing specific numbers and organization names
- Hallucinated proper nouns not present in the source transcript
- Mid-sentence truncation at the word limit

The redesigned prompt + sentence-boundary truncation address all four.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from scripts.eval_summary_quality import (
    coverage_score,
    hallucinated_proper_nouns,
    word_count,
)
from social_research_probe.pipeline.enrichment import (
    _build_summary_prompt,
    _fallback_transcript_summary,
)

FIXTURES = Path(__file__).resolve().parent.parent.parent / "fixtures" / "golden" / "transcripts"


def _load_spec(name: str) -> dict:
    return json.loads((FIXTURES / f"{name}.keyphrases.json").read_text())


# ---------------------------------------------------------------------------
# coverage_score — fraction of required tokens
# ---------------------------------------------------------------------------


def test_coverage_score_returns_one_when_all_tokens_present():
    summary = "Claude 3.5 Sonnet scores 96.4 on GSM8K."
    assert coverage_score(summary, ["Claude", "3.5 Sonnet", "96.4", "GSM8K"]) == 1.0


def test_coverage_score_returns_half_when_half_missing():
    summary = "Some unrelated text with no keyphrases."
    score = coverage_score(summary, ["Claude", "some", "no", "absent"])
    # "some" and "no" match → 2/4.
    assert score == pytest.approx(0.5)


def test_coverage_score_handles_empty_keyphrase_list():
    assert coverage_score("any text", []) == 1.0


# ---------------------------------------------------------------------------
# hallucinated_proper_nouns — capitalized tokens not in source
# ---------------------------------------------------------------------------


def test_hallucinated_proper_nouns_flags_names_absent_from_transcript():
    transcript = "Anthropic released Claude 3.5 Sonnet."
    summary = "Anthropic's Claude 3.5 Sonnet was announced by Zuckerberg in Menlo."
    hallucinations = hallucinated_proper_nouns(
        summary, transcript, allowed=["Anthropic", "Claude", "Sonnet"]
    )
    assert "Zuckerberg" in hallucinations
    assert "Menlo" in hallucinations
    assert "Claude" not in hallucinations


def test_hallucinated_proper_nouns_empty_when_summary_is_faithful():
    transcript = "The European Union fined Meta 1.2 billion euros for GDPR violations."
    summary = "Meta was fined 1.2 billion euros by the European Union for GDPR."
    hallucinations = hallucinated_proper_nouns(
        summary,
        transcript,
        allowed=["Meta", "European Union", "GDPR", "EU"],
    )
    assert hallucinations == []


# ---------------------------------------------------------------------------
# Prompt redesign — anti-hallucination + filler blocklist + exemplar
# ---------------------------------------------------------------------------


def test_build_summary_prompt_includes_anti_hallucination_and_filler_rules():
    prompt = _build_summary_prompt(
        title="t", channel="c", transcript="transcript body", word_limit=100
    )
    # Anti-hallucination clause
    assert "Never introduce information that isn't in the transcript" in prompt
    # Filler blocklist — at least one concrete forbidden phrase
    assert "This video" in prompt
    # One-shot exemplar
    assert "EXAMPLE INPUT" in prompt
    assert "EXAMPLE OUTPUT" in prompt
    # Hard word cap
    assert "at most 100 words" in prompt
    # Sentence-boundary rule
    assert "complete sentence" in prompt


# ---------------------------------------------------------------------------
# _fallback_transcript_summary — sentence-boundary truncation
# ---------------------------------------------------------------------------


def test_fallback_truncates_at_sentence_boundary_when_possible():
    """When the first 100 words end inside a sentence, truncate at the last
    complete sentence in the upper half — no mid-word ellipsis."""
    # 50-word first sentence, then 100 more words in a long second sentence.
    first_sentence = " ".join(f"alpha{i}" for i in range(50)) + "."
    second_half = " ".join(f"beta{i}" for i in range(100))
    transcript = first_sentence + " " + second_half
    out = _fallback_transcript_summary(transcript, word_limit=100)
    # Must end with the sentence-terminator, not the ellipsis marker.
    assert out.endswith(".")
    assert not out.endswith(" ...")
    # Must be strictly fewer than 100 words (since we truncated at sentence).
    assert word_count(out) <= 100


def test_fallback_falls_back_to_word_cut_when_no_sentence_boundary():
    """If the transcript has no terminator in the upper half of the cut,
    fall back to the ellipsis marker — so tests that relied on ' ...' still
    see it for those inputs."""
    transcript = " ".join(f"w{i}" for i in range(200))  # no punctuation
    out = _fallback_transcript_summary(transcript, word_limit=100)
    assert out.endswith(" ...")


def test_fallback_returns_full_transcript_when_within_limit():
    short = "One. Two. Three."
    assert _fallback_transcript_summary(short, word_limit=100) == "One. Two. Three."


# ---------------------------------------------------------------------------
# Keyphrase fixtures are well-formed and cover the transcript
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", ["sample_tech_talk", "sample_news_brief"])
def test_reference_keyphrases_appear_in_source_transcript(name):
    """Sanity check: every required token in a keyphrase JSON must appear
    verbatim in its source transcript. If this fails, the fixture is broken
    and will make real-LLM coverage scoring inaccurate."""
    import re

    spec = _load_spec(name)
    transcript = (FIXTURES / spec["source_transcript"]).read_text(encoding="utf-8")
    # Collapse whitespace so multi-word tokens that straddle VTT line wrap
    # ("Irish Data Protection Commission") still match.
    normalized = re.sub(r"\s+", " ", transcript).lower()
    missing = [t for t in spec["required_tokens"] if t.lower() not in normalized]
    assert missing == [], f"keyphrases missing from transcript: {missing}"
