"""Tests for compute_quality_score helper."""

from __future__ import annotations

import pytest

from social_research_probe.utils.claims.quality import compute_quality_score


def _perfect_claim() -> dict:
    return {
        "confidence": 1.0,
        "evidence_tier": "metadata_transcript",
        "corroboration_status": "supported",
        "extraction_method": "llm",
        "position_in_text": 42,
    }


def _minimal_claim() -> dict:
    return {
        "confidence": 0.0,
        "evidence_tier": "metadata_only",
        "corroboration_status": "refuted",
        "extraction_method": "deterministic",
        "position_in_text": 0,
    }


def test_perfect_claim_high_score():
    score = compute_quality_score(_perfect_claim())
    assert score == pytest.approx(0.30 + 0.25 + 0.20 + 0.15 * 0.9 + 0.10, abs=0.01)


def test_minimal_claim_low_score():
    score = compute_quality_score(_minimal_claim())
    expected = 0.30 * 0.0 + 0.25 * 0.4 + 0.20 * 0.0 + 0.15 * 0.6 + 0.10 * 0.5
    assert score == pytest.approx(expected, abs=0.01)


def test_confidence_factor_affects_score():
    low = compute_quality_score({**_perfect_claim(), "confidence": 0.2})
    high = compute_quality_score({**_perfect_claim(), "confidence": 0.9})
    assert high > low


def test_evidence_tier_factor_affects_score():
    low = compute_quality_score({**_perfect_claim(), "evidence_tier": "metadata_only"})
    high = compute_quality_score({**_perfect_claim(), "evidence_tier": "metadata_transcript"})
    assert high > low


def test_corroboration_factor_affects_score():
    low = compute_quality_score({**_perfect_claim(), "corroboration_status": "refuted"})
    high = compute_quality_score({**_perfect_claim(), "corroboration_status": "supported"})
    assert high > low


def test_method_factor_affects_score():
    low = compute_quality_score({**_perfect_claim(), "extraction_method": "deterministic"})
    high = compute_quality_score({**_perfect_claim(), "extraction_method": "llm"})
    assert high > low


def test_grounding_factor_affects_score():
    low = compute_quality_score({**_perfect_claim(), "position_in_text": 0})
    high = compute_quality_score({**_perfect_claim(), "position_in_text": 10})
    assert high > low


def test_unknown_tier_defaults_to_half():
    score = compute_quality_score({**_perfect_claim(), "evidence_tier": "unknown_tier"})
    default_score = compute_quality_score(
        {**_perfect_claim(), "evidence_tier": "metadata_comments"}
    )
    assert score != default_score


def test_unknown_corroboration_defaults_to_half():
    score = compute_quality_score({**_perfect_claim(), "corroboration_status": "weird"})
    half_tier = 0.5
    expected_corr_contribution = 0.20 * half_tier
    base = compute_quality_score(_perfect_claim())
    supported_contribution = 0.20 * 1.0
    assert score == pytest.approx(
        base - supported_contribution + expected_corr_contribution, abs=0.01
    )


def test_unknown_method_defaults_to_half():
    score = compute_quality_score({**_perfect_claim(), "extraction_method": "banana"})
    base = compute_quality_score(_perfect_claim())
    diff = base - score
    assert diff == pytest.approx(0.15 * (0.9 - 0.5), abs=0.01)


def test_missing_fields_no_crash():
    score = compute_quality_score({})
    assert 0.0 <= score <= 1.0


def test_score_always_in_range():
    for conf in [-1.0, 0.0, 0.5, 1.0, 2.0]:
        score = compute_quality_score({"confidence": conf})
        assert 0.0 <= score <= 1.0


def test_deterministic_same_input_same_output():
    claim = _perfect_claim()
    assert compute_quality_score(claim) == compute_quality_score(claim)


def test_position_zero_vs_positive():
    zero = compute_quality_score({"position_in_text": 0})
    positive = compute_quality_score({"position_in_text": 1})
    assert positive > zero
