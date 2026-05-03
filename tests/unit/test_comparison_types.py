"""Tests for comparison type definitions."""

from __future__ import annotations

from typing import get_type_hints

from social_research_probe.utils.comparison.types import (
    ChangeStatus,
    ClaimChange,
    ComparisonResult,
    NarrativeChange,
    RunInfo,
    SourceChange,
    TrendSignal,
)


class TestSourceChange:
    def test_has_all_fields(self) -> None:
        hints = get_type_hints(SourceChange)
        expected = {
            "source_id", "platform", "external_id", "url", "title",
            "status", "score_changes", "evidence_tier_baseline", "evidence_tier_target",
        }
        assert set(hints.keys()) == expected


class TestClaimChange:
    def test_has_all_fields(self) -> None:
        hints = get_type_hints(ClaimChange)
        expected = {
            "claim_id", "claim_text", "claim_type", "source_url", "status",
            "confidence_change", "corroboration_changed",
            "baseline_corroboration", "target_corroboration", "review_status_changed",
        }
        assert set(hints.keys()) == expected


class TestNarrativeChange:
    def test_has_all_fields(self) -> None:
        hints = get_type_hints(NarrativeChange)
        expected = {
            "narrative_id", "title", "cluster_type", "status",
            "match_method", "matched_id", "confidence_change",
            "opportunity_change", "risk_change",
            "claim_count_change", "source_count_change", "strength_signal",
        }
        assert set(hints.keys()) == expected


class TestTrendSignal:
    def test_has_all_fields(self) -> None:
        hints = get_type_hints(TrendSignal)
        expected = {"signal_type", "title", "description", "narrative_id", "score"}
        assert set(hints.keys()) == expected


class TestRunInfo:
    def test_has_all_fields(self) -> None:
        hints = get_type_hints(RunInfo)
        expected = {
            "run_pk", "run_id", "topic", "platform",
            "started_at", "finished_at",
            "source_count", "claim_count", "narrative_count",
        }
        assert set(hints.keys()) == expected


class TestComparisonResult:
    def test_has_all_fields(self) -> None:
        hints = get_type_hints(ComparisonResult)
        expected = {
            "baseline", "target", "source_changes", "claim_changes",
            "narrative_changes", "trends", "counts", "follow_ups",
        }
        assert set(hints.keys()) == expected


class TestChangeStatus:
    def test_literal_values(self) -> None:
        assert ChangeStatus.__args__ == ("new", "repeated", "disappeared")
