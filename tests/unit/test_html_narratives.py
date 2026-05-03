"""Tests for section_narratives HTML builder."""

from __future__ import annotations

from social_research_probe.technologies.report_render.html.raw_html._sections import (
    section_narratives,
)


def _cluster(cluster_type: str = "theme", title: str = "theme: AI", **kwargs: object) -> dict:
    base = {
        "narrative_id": "n1",
        "title": title,
        "cluster_type": cluster_type,
        "claim_count": 3,
        "source_count": 2,
        "confidence": 0.75,
        "opportunity_score": 0.4,
        "risk_score": 0.1,
    }
    base.update(kwargs)
    return base


class TestSectionNarratives:
    def test_non_empty_clusters_renders_table(self) -> None:
        report = {"narratives": [_cluster()]}
        html = section_narratives(report)
        assert "<table>" in html
        assert "Narrative Clusters (1)" in html
        assert "<details" in html

    def test_empty_clusters_returns_empty(self) -> None:
        report = {"narratives": []}
        assert section_narratives(report) == ""

    def test_no_narratives_key_returns_empty(self) -> None:
        report = {}
        assert section_narratives(report) == ""

    def test_sorted_by_opportunity_desc(self) -> None:
        report = {
            "narratives": [
                _cluster(title="low", opportunity_score=0.1),
                _cluster(title="high", opportunity_score=0.9),
            ]
        }
        html = section_narratives(report)
        high_pos = html.index("high")
        low_pos = html.index("low")
        assert high_pos < low_pos

    def test_html_escapes_title(self) -> None:
        report = {"narratives": [_cluster(title="<script>alert('xss')</script>")]}
        html = section_narratives(report)
        assert "<script>" not in html
        assert "&lt;script&gt;" in html
