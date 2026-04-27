"""Tests for utils.core.dedupe."""

from __future__ import annotations

from social_research_probe.utils.core.dedupe import (
    DUPLICATE_THRESHOLD,
    NEAR_DUPLICATE_THRESHOLD,
    DedupeResult,
    DuplicateStatus,
    classify,
)


class TestClassify:
    def test_empty_existing_is_new(self):
        result = classify("hello", [])
        assert result.status == DuplicateStatus.NEW
        assert result.matches == ()

    def test_exact_match_is_duplicate(self):
        result = classify("AI agents", ["AI agents"])
        assert result.status == DuplicateStatus.DUPLICATE
        assert "AI agents" in result.matches

    def test_case_insensitive_duplicate(self):
        result = classify("ai AGENTS", ["AI agents"])
        assert result.status == DuplicateStatus.DUPLICATE

    def test_unrelated_is_new(self):
        result = classify("apples", ["bananas", "carrots"])
        assert result.status == DuplicateStatus.NEW

    def test_returns_dedupe_result_dataclass(self):
        result = classify("foo", [])
        assert isinstance(result, DedupeResult)


class TestThresholds:
    def test_threshold_constants(self):
        assert DUPLICATE_THRESHOLD == 95
        assert NEAR_DUPLICATE_THRESHOLD == 80
