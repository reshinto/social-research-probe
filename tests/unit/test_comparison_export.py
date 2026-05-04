"""Tests for comparison export writers."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from social_research_probe.utils.comparison.export import (
    CLAIM_COLUMNS,
    NARRATIVE_COLUMNS,
    SOURCE_COLUMNS,
    write_comparison_artifacts,
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
        topic="AI",
        platform="youtube",
        started_at="2024-01-01",
        finished_at="2024-01-01",
        source_count=5,
        claim_count=10,
        narrative_count=3,
    )


def _result_with_data() -> ComparisonResult:
    return ComparisonResult(
        baseline=_run_info("run-a", 1),
        target=_run_info("run-b", 2),
        source_changes=[
            SourceChange(
                source_id=1,
                platform="youtube",
                external_id="v1",
                url="https://yt/v1",
                title="Video 1",
                status="new",
                score_changes={"trust": 0.1, "overall": -0.05},
                evidence_tier_baseline="",
                evidence_tier_target="full",
            ),
        ],
        claim_changes=[
            ClaimChange(
                claim_id="c1",
                claim_text="Claim A",
                claim_type="fact",
                source_url="https://yt/v1",
                status="repeated",
                confidence_change=0.1,
                corroboration_changed=True,
                baseline_corroboration="pending",
                target_corroboration="confirmed",
                review_status_changed=False,
            ),
        ],
        narrative_changes=[
            NarrativeChange(
                narrative_id="n1",
                title="AI Theme",
                cluster_type="theme",
                status="repeated",
                match_method="exact_id",
                matched_id="n1",
                confidence_change=0.2,
                opportunity_change=0.1,
                risk_change=-0.05,
                claim_count_change=2,
                source_count_change=1,
                strength_signal="strengthened",
            ),
        ],
        trends=[
            TrendSignal(
                signal_type="rising_risk",
                title="Rising",
                description="desc",
                narrative_id="n1",
                score=0.8,
            ),
        ],
        counts={"sources": 5, "claims": 10},
        follow_ups=["Investigate something"],
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


class TestWriteComparisonArtifacts:
    def test_creates_four_files(self, tmp_path: Path) -> None:
        result = write_comparison_artifacts(_result_with_data(), tmp_path)
        assert len(result) == 4
        for path_str in result.values():
            assert Path(path_str).exists()

    def test_stem_naming(self, tmp_path: Path) -> None:
        result = write_comparison_artifacts(_result_with_data(), tmp_path)
        for path_str in result.values():
            assert "compare-1-vs-2" in Path(path_str).name

    def test_sources_csv_columns(self, tmp_path: Path) -> None:
        paths = write_comparison_artifacts(_result_with_data(), tmp_path)
        with open(paths["sources_csv"]) as f:
            reader = csv.DictReader(f)
            assert list(reader.fieldnames) == SOURCE_COLUMNS

    def test_claims_csv_columns(self, tmp_path: Path) -> None:
        paths = write_comparison_artifacts(_result_with_data(), tmp_path)
        with open(paths["claims_csv"]) as f:
            reader = csv.DictReader(f)
            assert list(reader.fieldnames) == CLAIM_COLUMNS

    def test_narratives_csv_columns(self, tmp_path: Path) -> None:
        paths = write_comparison_artifacts(_result_with_data(), tmp_path)
        with open(paths["narratives_csv"]) as f:
            reader = csv.DictReader(f)
            assert list(reader.fieldnames) == NARRATIVE_COLUMNS

    def test_json_valid(self, tmp_path: Path) -> None:
        paths = write_comparison_artifacts(_result_with_data(), tmp_path)
        with open(paths["summary_json"]) as f:
            data = json.load(f)
        assert "baseline" in data
        assert "target" in data
        assert "source_changes" in data

    def test_empty_changes_header_only_csv(self, tmp_path: Path) -> None:
        paths = write_comparison_artifacts(_empty_result(), tmp_path)
        with open(paths["sources_csv"]) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert rows == []

    def test_creates_output_dir(self, tmp_path: Path) -> None:
        nested = tmp_path / "a" / "b" / "c"
        write_comparison_artifacts(_empty_result(), nested)
        assert nested.exists()

    def test_csv_roundtrip_data(self, tmp_path: Path) -> None:
        paths = write_comparison_artifacts(_result_with_data(), tmp_path)
        with open(paths["sources_csv"]) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 1
        assert rows[0]["source_id"] == "1"
        assert rows[0]["status"] == "new"
        assert rows[0]["trust_change"] == "0.1"
