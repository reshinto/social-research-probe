"""Tests for narrative clustering type definitions."""

from __future__ import annotations

from typing import get_type_hints

from social_research_probe.utils.narratives.types import (
    CLUSTER_TYPE_VALUES,
    NarrativeCluster,
)


class TestNarrativeClusterTypedDict:
    def test_has_all_expected_fields(self) -> None:
        hints = get_type_hints(NarrativeCluster)
        expected = {
            "narrative_id",
            "title",
            "summary",
            "cluster_type",
            "claim_ids",
            "source_ids",
            "source_urls",
            "representative_claims",
            "entities",
            "keywords",
            "evidence_tiers",
            "corroboration_statuses",
            "source_count",
            "claim_count",
            "confidence",
            "opportunity_score",
            "risk_score",
            "contradiction_count",
            "needs_review_count",
            "created_at",
        }
        assert set(hints.keys()) == expected

    def test_cluster_type_values_match_literal(self) -> None:
        expected = {
            "theme",
            "objection",
            "pain_point",
            "opportunity",
            "market_signal",
            "question",
            "prediction",
            "mixed",
        }
        assert expected == CLUSTER_TYPE_VALUES
