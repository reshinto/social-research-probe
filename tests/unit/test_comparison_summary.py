"""Tests for comparison summary and follow-ups."""

from __future__ import annotations

from social_research_probe.utils.comparison.summary import (
    build_counts,
    build_follow_ups,
    format_console_summary,
)
from social_research_probe.utils.comparison.types import (
    ClaimChange,
    ComparisonResult,
    NarrativeChange,
    RunInfo,
    SourceChange,
    TrendSignal,
)


def _run_info(run_id: str = "run-a", run_pk: int = 1) -> RunInfo:
    return RunInfo(
        run_pk=run_pk,
        run_id=run_id,
        topic="AI agents",
        platform="youtube",
        started_at="2024-01-01",
        finished_at="2024-01-01",
        source_count=5,
        claim_count=10,
        narrative_count=3,
    )


def _empty_result() -> ComparisonResult:
    return ComparisonResult(
        baseline=_run_info("run-a", 1),
        target=_run_info("run-b", 2),
        source_changes=[],
        claim_changes=[],
        narrative_changes=[],
        trends=[],
        counts={},
        follow_ups=[],
    )


def _result_with_changes() -> ComparisonResult:
    return ComparisonResult(
        baseline=_run_info("run-a", 1),
        target=_run_info("run-b", 2),
        source_changes=[
            SourceChange(source_id=1, platform="yt", external_id="v1", url="",
                         title="V1", status="new", score_changes={},
                         evidence_tier_baseline="", evidence_tier_target="full"),
            SourceChange(source_id=2, platform="yt", external_id="v2", url="",
                         title="V2", status="repeated", score_changes={},
                         evidence_tier_baseline="full", evidence_tier_target="full"),
        ],
        claim_changes=[
            ClaimChange(claim_id="c1", claim_text="X", claim_type="fact",
                        source_url="", status="new", confidence_change=0.0,
                        corroboration_changed=False, baseline_corroboration="",
                        target_corroboration="pending", review_status_changed=False),
            ClaimChange(claim_id="c2", claim_text="Y", claim_type="fact",
                        source_url="", status="repeated", confidence_change=0.1,
                        corroboration_changed=True, baseline_corroboration="pending",
                        target_corroboration="confirmed", review_status_changed=False),
            ClaimChange(claim_id="c3", claim_text="Z", claim_type="fact",
                        source_url="", status="disappeared", confidence_change=0.0,
                        corroboration_changed=False, baseline_corroboration="supported",
                        target_corroboration="", review_status_changed=False),
        ],
        narrative_changes=[
            NarrativeChange(narrative_id="n1", title="AI Theme", cluster_type="theme",
                            status="repeated", match_method="exact_id", matched_id="n1",
                            confidence_change=0.2, opportunity_change=0.0, risk_change=0.0,
                            claim_count_change=2, source_count_change=1,
                            strength_signal="strengthened"),
            NarrativeChange(narrative_id="n2", title="Weak One", cluster_type="theme",
                            status="repeated", match_method="exact_id", matched_id="n2",
                            confidence_change=-0.2, opportunity_change=0.0, risk_change=0.0,
                            claim_count_change=-1, source_count_change=0,
                            strength_signal="weakened"),
            NarrativeChange(narrative_id="n3", title="New Narrative", cluster_type="theme",
                            status="new", match_method="", matched_id="",
                            confidence_change=0.0, opportunity_change=0.0, risk_change=0.0,
                            claim_count_change=0, source_count_change=0,
                            strength_signal=""),
        ],
        trends=[
            TrendSignal(signal_type="emerging_narrative", title="Emerging: New Narrative",
                        description="desc", narrative_id="n3", score=0.8),
        ],
        follow_ups=["Investigate emerging narrative: New Narrative"],
    )


class TestBuildCounts:
    def test_empty_result(self) -> None:
        counts = build_counts(_empty_result())
        assert counts["sources_new"] == 0
        assert counts["claims_new"] == 0
        assert counts["narratives_new"] == 0
        assert counts["trend_count"] == 0

    def test_correct_counts(self) -> None:
        counts = build_counts(_result_with_changes())
        assert counts["sources_new"] == 1
        assert counts["sources_repeated"] == 1
        assert counts["sources_disappeared"] == 0
        assert counts["claims_new"] == 1
        assert counts["claims_repeated"] == 1
        assert counts["claims_disappeared"] == 1
        assert counts["narratives_new"] == 1
        assert counts["narratives_repeated"] == 2
        assert counts["narratives_strengthened"] == 1
        assert counts["narratives_weakened"] == 1
        assert counts["trend_count"] == 1


class TestFormatConsoleSummary:
    def test_contains_run_ids(self) -> None:
        output = format_console_summary(_result_with_changes())
        assert "run-a" in output
        assert "run-b" in output

    def test_contains_sections(self) -> None:
        output = format_console_summary(_result_with_changes())
        assert "Sources:" in output
        assert "Claims:" in output
        assert "Narratives:" in output

    def test_contains_trend_signals(self) -> None:
        output = format_console_summary(_result_with_changes())
        assert "Trend Signals:" in output
        assert "emerging_narrative" in output

    def test_contains_follow_ups(self) -> None:
        output = format_console_summary(_result_with_changes())
        assert "Follow-ups:" in output

    def test_empty_result_no_crash(self) -> None:
        output = format_console_summary(_empty_result())
        assert "run-a" in output
        assert "Trend Signals:" not in output


class TestBuildFollowUps:
    def test_empty_result(self) -> None:
        result = _empty_result()
        assert build_follow_ups(result) == []

    def test_new_narrative_suggestion(self) -> None:
        result = _result_with_changes()
        follow_ups = build_follow_ups(result)
        assert any("emerging narrative" in f.lower() or "New Narrative" in f for f in follow_ups)

    def test_corroboration_change_suggestion(self) -> None:
        result = _result_with_changes()
        follow_ups = build_follow_ups(result)
        assert any("corroboration" in f.lower() for f in follow_ups)

    def test_weakening_narrative_suggestion(self) -> None:
        result = _result_with_changes()
        follow_ups = build_follow_ups(result)
        assert any("weakening" in f.lower() or "Weak One" in f for f in follow_ups)

    def test_new_sources_suggestion(self) -> None:
        result = _result_with_changes()
        follow_ups = build_follow_ups(result)
        assert any("source" in f.lower() for f in follow_ups)

    def test_max_5_follow_ups(self) -> None:
        result = _result_with_changes()
        result["narrative_changes"] = [
            NarrativeChange(narrative_id=f"n{i}", title=f"New {i}", cluster_type="theme",
                            status="new", match_method="", matched_id="",
                            confidence_change=0.0, opportunity_change=0.0, risk_change=0.0,
                            claim_count_change=0, source_count_change=0, strength_signal="")
            for i in range(10)
        ]
        follow_ups = build_follow_ups(result)
        assert len(follow_ups) <= 5
