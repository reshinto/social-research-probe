"""rapidfuzz-backed dedupe: exact -> duplicate, near -> near-duplicate, else -> new."""
from __future__ import annotations

from social_research_probe.dedupe import DuplicateStatus, classify


def test_exact_match_is_duplicate():
    result = classify("ai agents", existing=["ai agents", "robotics"])
    assert result.status is DuplicateStatus.DUPLICATE
    assert result.matches == ("ai agents",)


def test_case_and_whitespace_insensitive():
    result = classify("  AI Agents  ", existing=["ai agents"])
    assert result.status is DuplicateStatus.DUPLICATE


def test_near_match_is_near_duplicate():
    result = classify("ai agent", existing=["ai agents"])
    assert result.status is DuplicateStatus.NEAR_DUPLICATE
    assert "ai agents" in result.matches


def test_unrelated_is_new():
    result = classify("quantum computing", existing=["ai agents", "robotics"])
    assert result.status is DuplicateStatus.NEW
    assert result.matches == ()


def test_empty_existing_is_new():
    result = classify("anything", existing=[])
    assert result.status is DuplicateStatus.NEW


def test_threshold_is_documented():
    from social_research_probe.dedupe import DUPLICATE_THRESHOLD, NEAR_DUPLICATE_THRESHOLD
    assert DUPLICATE_THRESHOLD == 95
    assert NEAR_DUPLICATE_THRESHOLD == 80
    assert NEAR_DUPLICATE_THRESHOLD < DUPLICATE_THRESHOLD


def test_all_normalized_duplicates_returned():
    result = classify("AI Agents", existing=["AI Agents", "ai agents"])
    assert result.status is DuplicateStatus.DUPLICATE
    assert len(result.matches) == 2
    assert "AI Agents" in result.matches
    assert "ai agents" in result.matches
