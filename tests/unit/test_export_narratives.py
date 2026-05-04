"""Tests for narrative export: CSV builder, run_summary narratives, methodology section."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from social_research_probe.technologies.report_render.export.methodology_md import (
    build_methodology,
)
from social_research_probe.technologies.report_render.export.narratives_csv import (
    NARRATIVES_COLUMNS,
    build_narratives_rows,
    write_narratives_csv,
)
from social_research_probe.technologies.report_render.export.run_summary_json import (
    build_run_summary,
)


def _cluster(
    narrative_id: str = "abc123",
    cluster_type: str = "theme",
    claim_count: int = 3,
    source_count: int = 2,
    confidence: float = 0.7,
    opportunity_score: float = 0.3,
    risk_score: float = 0.1,
) -> dict:
    return {
        "narrative_id": narrative_id,
        "title": f"{cluster_type}: AI",
        "cluster_type": cluster_type,
        "claim_count": claim_count,
        "source_count": source_count,
        "confidence": confidence,
        "opportunity_score": opportunity_score,
        "risk_score": risk_score,
        "contradiction_count": 0,
        "needs_review_count": 0,
        "entities": ["AI", "ML"],
        "keywords": ["artificial intelligence"],
        "evidence_tiers": ["transcript_rich"],
        "corroboration_statuses": ["supported"],
        "representative_claims": ["AI is transformative"],
        "source_urls": ["https://example.com/v1"],
        "claim_ids": ["c1", "c2", "c3"],
        "created_at": "2024-01-01T00:00:00",
    }


class TestNarrativesCsvBuilder:
    def test_build_rows_correct_count(self) -> None:
        clusters = [_cluster("n1"), _cluster("n2")]
        rows = build_narratives_rows(clusters)
        assert len(rows) == 2

    def test_build_rows_columns_match(self) -> None:
        rows = build_narratives_rows([_cluster()])
        row = rows[0]
        for col in NARRATIVES_COLUMNS:
            assert col in row

    def test_build_rows_empty_clusters(self) -> None:
        assert build_narratives_rows([]) == []

    def test_list_fields_joined(self) -> None:
        rows = build_narratives_rows([_cluster()])
        row = rows[0]
        assert row["entities"] == "AI; ML"
        assert row["keywords"] == "artificial intelligence"
        assert row["claim_ids"] == "c1; c2; c3"

    def test_non_dict_filtered(self) -> None:
        rows = build_narratives_rows([_cluster(), "invalid", None, 42])
        assert len(rows) == 1

    def test_write_csv_creates_file(self, tmp_path: Path) -> None:
        rows = build_narratives_rows([_cluster()])
        path = tmp_path / "narratives.csv"
        result = write_narratives_csv(rows, path)
        assert result == path
        assert path.exists()
        lines = path.read_text().splitlines()
        assert lines[0] == ",".join(NARRATIVES_COLUMNS)
        assert len(lines) == 2

    def test_write_csv_empty_rows_header_only(self, tmp_path: Path) -> None:
        path = tmp_path / "narratives.csv"
        write_narratives_csv([], path)
        lines = path.read_text().splitlines()
        assert len(lines) == 1
        assert lines[0] == ",".join(NARRATIVES_COLUMNS)


class TestRunSummaryNarratives:
    def test_narratives_summary_present(self) -> None:
        report = {"narratives": [_cluster()]}
        summary = build_run_summary(report, {}, {})
        assert "narratives_summary" in summary

    def test_narratives_summary_keys(self) -> None:
        report = {"narratives": [_cluster("n1", "theme"), _cluster("n2", "risk")]}
        summary = build_run_summary(report, {}, {})
        ns = summary["narratives_summary"]
        assert ns["cluster_count"] == 2
        assert "theme" in ns["by_type"]
        assert "risk" in ns["by_type"]
        assert ns["total_claims_clustered"] == 6
        assert len(ns["top_opportunities"]) <= 3
        assert len(ns["top_risks"]) <= 3

    def test_narratives_summary_empty(self) -> None:
        report = {"narratives": []}
        summary = build_run_summary(report, {}, {})
        ns = summary["narratives_summary"]
        assert ns["cluster_count"] == 0
        assert ns["avg_confidence"] == 0.0
        assert ns["total_claims_clustered"] == 0

    def test_narratives_summary_no_key(self) -> None:
        report = {}
        summary = build_run_summary(report, {}, {})
        ns = summary["narratives_summary"]
        assert ns["cluster_count"] == 0

    def test_top_opportunities_sorted(self) -> None:
        report = {
            "narratives": [
                _cluster("n1", opportunity_score=0.9),
                _cluster("n2", opportunity_score=0.3),
                _cluster("n3", opportunity_score=0.6),
            ]
        }
        summary = build_run_summary(report, {}, {})
        opps = summary["narratives_summary"]["top_opportunities"]
        scores = [o["opportunity_score"] for o in opps]
        assert scores == sorted(scores, reverse=True)


class TestMethodologyNarratives:
    def test_methodology_includes_narrative_section(self) -> None:
        config = {"narratives": {"min_cluster_size": 3, "max_cluster_size": 10}}
        content = build_methodology({}, config)
        assert "## Narrative Clustering" in content
        assert "Minimum cluster size: 3" in content
        assert "Maximum cluster size: 10" in content

    def test_methodology_llm_disabled_by_default(self) -> None:
        content = build_methodology({}, {})
        assert "LLM summarization: disabled" in content

    def test_methodology_llm_enabled(self) -> None:
        config = {"narratives": {"llm_summarize": True}}
        content = build_methodology({}, config)
        assert "LLM summarization: enabled" in content


class TestExportPackageNarrativesCsv:
    def test_export_writes_narratives_csv(self, tmp_path: Path) -> None:
        import asyncio

        from social_research_probe.technologies.report_render.export import ExportPackageTech

        report = {
            "topic": "test",
            "items_top_n": [],
            "narratives": [_cluster()],
        }
        data = {
            "report": report,
            "config": {"export": {"enabled": True, "narratives_csv": True}},
            "stem": "test",
            "reports_dir": str(tmp_path),
        }
        mock_cfg = MagicMock()
        mock_cfg.technology_enabled.return_value = True
        mock_cfg.debug_enabled.return_value = False

        with patch(
            "social_research_probe.technologies.load_active_config",
            return_value=mock_cfg,
        ):
            tech = ExportPackageTech()
            paths = asyncio.run(tech._execute(data))

        assert "narratives_csv" in paths
        csv_path = Path(paths["narratives_csv"])
        assert csv_path.exists()

    def test_export_skips_narratives_csv_when_disabled(self, tmp_path: Path) -> None:
        import asyncio

        from social_research_probe.technologies.report_render.export import ExportPackageTech

        report = {"topic": "test", "items_top_n": [], "narratives": [_cluster()]}
        data = {
            "report": report,
            "config": {"export": {"enabled": True, "narratives_csv": False}},
            "stem": "test",
            "reports_dir": str(tmp_path),
        }
        mock_cfg = MagicMock()
        mock_cfg.technology_enabled.return_value = True
        mock_cfg.debug_enabled.return_value = False

        with patch(
            "social_research_probe.technologies.load_active_config",
            return_value=mock_cfg,
        ):
            tech = ExportPackageTech()
            paths = asyncio.run(tech._execute(data))

        assert "narratives_csv" not in paths
