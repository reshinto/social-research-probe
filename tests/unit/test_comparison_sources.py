"""Tests for source comparison algorithm."""

from __future__ import annotations

import json

from social_research_probe.utils.comparison.sources import _parse_scores, compare_sources


def _src(
    source_id: int,
    external_id: str = "v1",
    scores: dict | None = None,
    evidence_tier: str = "metadata_only",
) -> dict:
    return {
        "source_id": source_id,
        "platform": "youtube",
        "external_id": external_id,
        "url": f"https://yt/{external_id}",
        "title": f"Video {external_id}",
        "scores_json": json.dumps(scores) if scores else None,
        "evidence_tier": evidence_tier,
    }


class TestParseScores:
    def test_valid_json(self) -> None:
        assert _parse_scores('{"trust": 0.8, "overall": 0.7}') == {"trust": 0.8, "overall": 0.7}

    def test_none_input(self) -> None:
        assert _parse_scores(None) == {}

    def test_empty_string(self) -> None:
        assert _parse_scores("") == {}

    def test_malformed_json(self) -> None:
        assert _parse_scores("{broken") == {}

    def test_non_dict_json(self) -> None:
        assert _parse_scores("[1, 2, 3]") == {}

    def test_filters_non_numeric_values(self) -> None:
        assert _parse_scores('{"trust": 0.8, "label": "high"}') == {"trust": 0.8}


class TestCompareSources:
    def test_empty_inputs(self) -> None:
        assert compare_sources([], []) == []

    def test_all_new(self) -> None:
        target = [_src(1, "v1"), _src(2, "v2")]
        result = compare_sources([], target)
        assert len(result) == 2
        assert all(r["status"] == "new" for r in result)

    def test_all_disappeared(self) -> None:
        baseline = [_src(1, "v1"), _src(2, "v2")]
        result = compare_sources(baseline, [])
        assert len(result) == 2
        assert all(r["status"] == "disappeared" for r in result)

    def test_mixed_status(self) -> None:
        baseline = [_src(1, "v1"), _src(2, "v2"), _src(3, "v3")]
        target = [_src(1, "v1"), _src(3, "v3"), _src(4, "v4")]
        result = compare_sources(baseline, target)
        statuses = {r["source_id"]: r["status"] for r in result}
        assert statuses[4] == "new"
        assert statuses[1] == "repeated"
        assert statuses[3] == "repeated"
        assert statuses[2] == "disappeared"

    def test_ordering_new_first_then_repeated_then_disappeared(self) -> None:
        baseline = [_src(1, "v1"), _src(2, "v2")]
        target = [_src(1, "v1"), _src(3, "v3")]
        result = compare_sources(baseline, target)
        statuses = [r["status"] for r in result]
        assert statuses == ["new", "repeated", "disappeared"]

    def test_score_changes_computed(self) -> None:
        baseline = [_src(1, "v1", scores={"trust": 0.8, "overall": 0.7})]
        target = [_src(1, "v1", scores={"trust": 0.9, "overall": 0.7})]
        result = compare_sources(baseline, target)
        assert result[0]["score_changes"] == {"trust": 0.1}

    def test_score_changes_negative(self) -> None:
        baseline = [_src(1, "v1", scores={"trust": 0.9})]
        target = [_src(1, "v1", scores={"trust": 0.7})]
        result = compare_sources(baseline, target)
        assert result[0]["score_changes"] == {"trust": -0.2}

    def test_no_score_change_empty_dict(self) -> None:
        baseline = [_src(1, "v1", scores={"trust": 0.8})]
        target = [_src(1, "v1", scores={"trust": 0.8})]
        result = compare_sources(baseline, target)
        assert result[0]["score_changes"] == {}

    def test_missing_scores_json_no_crash(self) -> None:
        baseline = [_src(1, "v1", scores=None)]
        target = [_src(1, "v1", scores={"trust": 0.5})]
        result = compare_sources(baseline, target)
        assert result[0]["score_changes"] == {"trust": 0.5}

    def test_evidence_tier_populated(self) -> None:
        baseline = [_src(1, "v1", evidence_tier="metadata_only")]
        target = [_src(1, "v1", evidence_tier="metadata_transcript")]
        result = compare_sources(baseline, target)
        assert result[0]["evidence_tier_baseline"] == "metadata_only"
        assert result[0]["evidence_tier_target"] == "metadata_transcript"

    def test_new_source_has_empty_baseline_tier(self) -> None:
        result = compare_sources([], [_src(1, "v1", evidence_tier="full")])
        assert result[0]["evidence_tier_baseline"] == ""
        assert result[0]["evidence_tier_target"] == "full"

    def test_disappeared_source_has_empty_target_tier(self) -> None:
        result = compare_sources([_src(1, "v1", evidence_tier="full")], [])
        assert result[0]["evidence_tier_target"] == ""
        assert result[0]["evidence_tier_baseline"] == "full"
