"""Tests for narrative comparison algorithm."""

from __future__ import annotations

import json

from social_research_probe.utils.comparison.narratives import (
    _parse_entities,
    compare_narratives,
    entity_jaccard,
)


def _narr(
    narrative_id: str = "n1",
    title: str = "AI Theme",
    cluster_type: str = "theme",
    entities: list[str] | None = None,
    confidence: float = 0.7,
    opportunity_score: float = 0.3,
    risk_score: float = 0.2,
    claim_count: int = 5,
    source_count: int = 2,
) -> dict:
    return {
        "narrative_id": narrative_id,
        "title": title,
        "cluster_type": cluster_type,
        "entities_json": json.dumps(entities) if entities is not None else None,
        "confidence": confidence,
        "opportunity_score": opportunity_score,
        "risk_score": risk_score,
        "claim_count": claim_count,
        "source_count": source_count,
    }


class TestParseEntities:
    def test_valid_list(self) -> None:
        assert _parse_entities('["AI", "ML"]') == {"ai", "ml"}

    def test_none_input(self) -> None:
        assert _parse_entities(None) == set()

    def test_empty_string(self) -> None:
        assert _parse_entities("") == set()

    def test_malformed_json(self) -> None:
        assert _parse_entities("{broken") == set()

    def test_non_list_json(self) -> None:
        assert _parse_entities('{"key": "val"}') == set()

    def test_filters_empty_strings(self) -> None:
        assert _parse_entities('["AI", "", "ML"]') == {"ai", "ml"}


class TestEntityJaccard:
    def test_identical_sets(self) -> None:
        assert entity_jaccard({"a", "b"}, {"a", "b"}) == 1.0

    def test_disjoint_sets(self) -> None:
        assert entity_jaccard({"a", "b"}, {"c", "d"}) == 0.0

    def test_partial_overlap(self) -> None:
        assert entity_jaccard({"a", "b", "c"}, {"b", "c", "d"}) == 0.5

    def test_both_empty(self) -> None:
        assert entity_jaccard(set(), set()) == 0.0


class TestCompareNarratives:
    def test_empty_inputs(self) -> None:
        assert compare_narratives([], []) == []

    def test_exact_id_match(self) -> None:
        baseline = [_narr("n1", confidence=0.7)]
        target = [_narr("n1", confidence=0.8)]
        result = compare_narratives(baseline, target)
        assert len(result) == 1
        assert result[0]["status"] == "repeated"
        assert result[0]["match_method"] == "exact_id"
        assert result[0]["matched_id"] == "n1"

    def test_fuzzy_match_entity_overlap(self) -> None:
        baseline = [_narr("n1", entities=["AI", "ML", "GPT", "LLM"])]
        target = [_narr("n99", entities=["AI", "ML", "GPT", "Transformer"])]
        result = compare_narratives(baseline, target)
        assert len(result) == 1
        assert result[0]["status"] == "repeated"
        assert result[0]["match_method"] == "entity_overlap"
        assert result[0]["matched_id"] == "n1"

    def test_fuzzy_no_match_low_jaccard(self) -> None:
        baseline = [_narr("n1", entities=["AI", "ML", "GPT", "LLM"])]
        target = [_narr("n2", entities=["Crypto", "Bitcoin", "ETH", "DeFi"])]
        result = compare_narratives(baseline, target)
        statuses = {r["narrative_id"]: r["status"] for r in result}
        assert statuses["n2"] == "new"
        assert statuses["n1"] == "disappeared"

    def test_different_cluster_type_prevents_fuzzy(self) -> None:
        baseline = [_narr("n1", cluster_type="theme", entities=["AI", "ML"])]
        target = [_narr("n2", cluster_type="objection", entities=["AI", "ML"])]
        result = compare_narratives(baseline, target)
        statuses = {r["narrative_id"]: r["status"] for r in result}
        assert statuses["n2"] == "new"
        assert statuses["n1"] == "disappeared"

    def test_strength_strengthened(self) -> None:
        baseline = [_narr("n1", claim_count=3, confidence=0.5)]
        target = [_narr("n1", claim_count=5, confidence=0.5)]
        result = compare_narratives(baseline, target)
        assert result[0]["strength_signal"] == "strengthened"

    def test_strength_weakened(self) -> None:
        baseline = [_narr("n1", confidence=0.8, claim_count=5)]
        target = [_narr("n1", confidence=0.5, claim_count=5)]
        result = compare_narratives(baseline, target)
        assert result[0]["strength_signal"] == "weakened"

    def test_strength_stable(self) -> None:
        baseline = [_narr("n1", confidence=0.7, claim_count=5)]
        target = [_narr("n1", confidence=0.7, claim_count=5)]
        result = compare_narratives(baseline, target)
        assert result[0]["strength_signal"] == "stable"

    def test_both_entities_empty_no_fuzzy(self) -> None:
        baseline = [_narr("n1", entities=[])]
        target = [_narr("n2", entities=[])]
        result = compare_narratives(baseline, target)
        statuses = {r["narrative_id"]: r["status"] for r in result}
        assert statuses["n2"] == "new"
        assert statuses["n1"] == "disappeared"

    def test_opportunity_and_risk_change(self) -> None:
        baseline = [_narr("n1", opportunity_score=0.3, risk_score=0.2)]
        target = [_narr("n1", opportunity_score=0.6, risk_score=0.1)]
        result = compare_narratives(baseline, target)
        assert result[0]["opportunity_change"] == 0.3
        assert result[0]["risk_change"] == -0.1

    def test_all_new(self) -> None:
        target = [_narr("n1"), _narr("n2")]
        result = compare_narratives([], target)
        assert all(r["status"] == "new" for r in result)

    def test_all_disappeared(self) -> None:
        baseline = [_narr("n1"), _narr("n2")]
        result = compare_narratives(baseline, [])
        assert all(r["status"] == "disappeared" for r in result)

    def test_malformed_entities_no_crash(self) -> None:
        baseline = [
            {
                "narrative_id": "n1",
                "title": "T",
                "cluster_type": "theme",
                "entities_json": "not valid json",
                "confidence": 0.5,
                "opportunity_score": 0.1,
                "risk_score": 0.1,
                "claim_count": 2,
                "source_count": 1,
            }
        ]
        target = [_narr("n2", entities=["AI"])]
        result = compare_narratives(baseline, target)
        assert len(result) == 2

    def test_ordering(self) -> None:
        baseline = [_narr("n1"), _narr("n2", entities=["X"])]
        target = [_narr("n1"), _narr("n3", entities=["Y"])]
        result = compare_narratives(baseline, target)
        statuses = [r["status"] for r in result]
        assert statuses == ["new", "repeated", "disappeared"]
