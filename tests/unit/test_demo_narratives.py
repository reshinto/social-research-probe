"""Tests for demo narrative clustering integration."""

from __future__ import annotations

from social_research_probe.utils.demo.fixtures import build_demo_report
from social_research_probe.utils.demo.narratives import build_demo_narratives


class TestDemoNarratives:
    def test_demo_items_produce_clusters(self) -> None:
        from social_research_probe.utils.demo.fixtures import build_demo_items

        items = build_demo_items()
        clusters = build_demo_narratives(items)
        assert len(clusters) >= 1

    def test_clusters_have_valid_narrative_ids(self) -> None:
        from social_research_probe.utils.demo.fixtures import build_demo_items

        clusters = build_demo_narratives(build_demo_items())
        for c in clusters:
            assert c["narrative_id"]
            assert len(c["narrative_id"]) == 16

    def test_report_narratives_populated(self) -> None:
        report = build_demo_report()
        assert "narratives" in report
        assert len(report["narratives"]) >= 1

    def test_clusters_have_required_fields(self) -> None:
        report = build_demo_report()
        for c in report["narratives"]:
            assert "cluster_type" in c
            assert "claim_count" in c
            assert "source_count" in c
            assert "confidence" in c
            assert c["claim_count"] >= 2
