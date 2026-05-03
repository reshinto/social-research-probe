"""Tests for the synthetic ResearchReport assembler used by the demo command."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch

from social_research_probe.commands._demo_constants import (
    DEMO_DISCLAIMER,
    DEMO_PURPOSE_SET,
)
from social_research_probe.commands._demo_fixtures import build_demo_report
from social_research_probe.commands._demo_items import build_demo_items

_FIXED_NOW = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)


def test_topic_marked_synthetic():
    report = build_demo_report()
    assert report["topic"].startswith("[SYNTHETIC DEMO]")


def test_disclaimer_first_warning():
    report = build_demo_report()
    assert report["warnings"][0] == DEMO_DISCLAIMER


def test_warnings_count_ge_3():
    report = build_demo_report()
    assert len(report["warnings"]) >= 3


def test_disclaimer_in_compiled_synthesis():
    report = build_demo_report()
    assert DEMO_DISCLAIMER in report["compiled_synthesis"]


def test_disclaimer_in_report_summary():
    report = build_demo_report()
    assert DEMO_DISCLAIMER in report["report_summary"]


def test_disclaimer_in_opportunity_analysis():
    report = build_demo_report()
    assert DEMO_DISCLAIMER in report["opportunity_analysis"]


def test_disclaimer_in_engagement_and_evidence_summary():
    report = build_demo_report()
    assert DEMO_DISCLAIMER in report["platform_engagement_summary"]
    assert DEMO_DISCLAIMER in report["evidence_summary"]


def test_items_count_matches_builder():
    report = build_demo_report()
    assert len(report["items_top_n"]) == len(build_demo_items())


def test_purpose_set_populated():
    report = build_demo_report()
    assert report["purpose_set"] == list(DEMO_PURPOSE_SET)


def test_platform_is_youtube():
    report = build_demo_report()
    assert report["platform"] == "youtube"


def test_source_validation_counts_match_items():
    report = build_demo_report()
    items = report["items_top_n"]
    summary = report["source_validation_summary"]
    bucketed = summary["primary"] + summary["secondary"] + summary["commentary"]
    unknowns = sum(1 for it in items if it.get("source_class") == "unknown")
    assert bucketed + unknowns == len(items)


def test_source_validation_verdict_counts():
    report = build_demo_report()
    items = report["items_top_n"]
    summary = report["source_validation_summary"]
    verified = sum(1 for it in items if it["corroboration_verdict"] == "verified")
    partial = sum(1 for it in items if it["corroboration_verdict"] == "partially_verified")
    unverified = sum(1 for it in items if it["corroboration_verdict"] == "unverified")
    assert summary["validated"] == verified
    assert summary["partially"] == partial
    assert summary["unverified"] == unverified


def test_source_validation_low_trust_count_matches():
    report = build_demo_report()
    items = report["items_top_n"]
    expected = sum(1 for it in items if it["scores"]["trust"] < 0.4)
    assert report["source_validation_summary"]["low_trust"] == expected


def test_stats_summary_shape():
    report = build_demo_report()
    stats = report["stats_summary"]
    assert stats["models_run"] == []
    assert isinstance(stats["highlights"], list)
    assert len(stats["highlights"]) >= 3
    assert stats["low_confidence"] is False


def test_chart_captions_and_takeaways_count():
    report = build_demo_report()
    assert 3 <= len(report["chart_captions"]) <= 5
    assert 3 <= len(report["chart_takeaways"]) <= 5


def test_stage_timings_shape():
    report = build_demo_report()
    timings = report["stage_timings"]
    assert len(timings) == 4
    for entry in timings:
        assert "stage" in entry
        assert "elapsed_s" in entry
        assert "status" in entry
        assert entry["status"] == "ok"


def test_no_html_or_export_paths_set():
    report = build_demo_report()
    assert "html_report_path" not in report
    assert "report_path" not in report
    assert "export_paths" not in report


def test_deterministic():
    with patch("social_research_probe.utils.claims.extractor.datetime") as mock_dt:
        mock_dt.now.return_value = _FIXED_NOW
        a = build_demo_report()
        b = build_demo_report()
    assert a == b


def test_disclaimer_in_chart_takeaway():
    report = build_demo_report()
    assert any(DEMO_DISCLAIMER in t for t in report["chart_takeaways"])


def test_source_validation_notes_non_empty():
    report = build_demo_report()
    assert report["source_validation_summary"]["notes"]
