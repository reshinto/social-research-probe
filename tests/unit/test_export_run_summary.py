"""Tests for Phase 3 run summary JSON builder."""

from __future__ import annotations

import copy
from pathlib import Path

from social_research_probe.technologies.report_render.export.run_summary_json import (
    build_run_summary,
    write_run_summary,
)
from social_research_probe.utils.io.io import read_json


def _minimal_report(**kwargs) -> dict:
    return {"topic": "AI safety", "platform": "youtube", **kwargs}


def _minimal_config(**kwargs) -> dict:
    return {
        "max_items": 20,
        "enrich_top_n": 5,
        "recency_days": 90,
        **kwargs,
    }


def _make_item(
    tier: str = "metadata_transcript", verdict: str | None = None, ts: str = "available"
) -> dict:
    item: dict = {"evidence_tier": tier, "transcript_status": ts}
    if verdict is not None:
        item["corroboration_verdict"] = verdict
    return item


def test_build_has_topic():
    out = build_run_summary(_minimal_report(), _minimal_config(), {})
    assert out["topic"] == "AI safety"


def test_build_has_platform():
    out = build_run_summary(_minimal_report(), _minimal_config(), {})
    assert out["platform"] == "youtube"


def test_build_timestamp_is_iso():
    out = build_run_summary(_minimal_report(), _minimal_config(), {})
    ts = out["timestamp"]
    assert isinstance(ts, str)
    assert "T" in ts


def test_build_has_item_counts():
    items = [_make_item(), _make_item(ts="unavailable"), _make_item(ts="not_attempted")]
    out = build_run_summary(_minimal_report(items_top_n=items), _minimal_config(), {})
    counts = out["item_count"]
    assert counts["fetched"] == 3
    assert counts["enriched"] == 2  # available + unavailable; not_attempted excluded


def test_build_has_evidence_tiers():
    items = [
        _make_item("metadata_transcript"),
        _make_item("metadata_transcript"),
        _make_item("metadata_only"),
    ]
    out = build_run_summary(_minimal_report(items_top_n=items), _minimal_config(), {})
    tiers = out["evidence_tiers"]
    assert tiers["metadata_transcript"] == 2
    assert tiers["metadata_only"] == 1


def test_build_has_corroboration_summary():
    items = [
        _make_item(verdict="verified"),
        _make_item(verdict="verified"),
        _make_item(verdict="unverified"),
        _make_item(),  # no verdict key
    ]
    out = build_run_summary(_minimal_report(items_top_n=items), _minimal_config(), {})
    corr = out["corroboration_summary"]
    assert corr["verified"] == 2
    assert corr["unverified"] == 1
    assert "unknown" not in corr  # item without key excluded


def test_build_artifact_paths_passed_through():
    paths = {"sources_csv": "/tmp/s.csv", "comments_csv": "/tmp/c.csv"}
    out = build_run_summary(_minimal_report(), _minimal_config(), paths)
    assert out["artifact_paths"] == paths


def test_build_config_snapshot_has_platform_config():
    out = build_run_summary(_minimal_report(), _minimal_config(), {})
    snap = out["config_snapshot"]
    assert "youtube" in snap
    assert snap["youtube"]["max_items"] == 20
    assert snap["youtube"]["enrich_top_n"] == 5
    assert snap["youtube"]["recency_days"] == 90


def test_build_has_warnings():
    report = _minimal_report(warnings=["low trust items"])
    out = build_run_summary(report, _minimal_config(), {})
    assert out["warnings"] == ["low trust items"]


def test_build_empty_report_no_crash():
    out = build_run_summary({}, {}, {})
    assert "topic" in out
    assert "timestamp" in out
    assert "item_count" in out
    assert out["item_count"]["fetched"] == 0


def test_write_creates_file(tmp_path: Path):
    summary = build_run_summary(_minimal_report(), _minimal_config(), {})
    out = tmp_path / "run_summary.json"
    result = write_run_summary(summary, out)
    assert out.exists()
    assert result == out


def test_write_roundtrip(tmp_path: Path):
    paths = {"sources_csv": "/tmp/s.csv"}
    summary = build_run_summary(_minimal_report(warnings=["w1"]), _minimal_config(), paths)
    out = tmp_path / "run_summary.json"
    write_run_summary(summary, out)
    loaded = read_json(out)
    assert loaded["topic"] == "AI safety"
    assert loaded["warnings"] == ["w1"]
    assert loaded["artifact_paths"] == paths


def test_build_does_not_mutate_inputs():
    report = _minimal_report(warnings=["w"])
    config = _minimal_config()
    paths = {"k": "v"}
    report_copy = copy.deepcopy(report)
    config_copy = copy.deepcopy(config)
    paths_copy = dict(paths)
    build_run_summary(report, config, paths)
    assert report == report_copy
    assert config == config_copy
    assert paths == paths_copy


def test_build_config_snapshot_no_scoring_weights_in_flat_config():
    """Regression: flat platform-level config snapshot omits scoring_weights (not in platform scope)."""
    out = build_run_summary(_minimal_report(), _minimal_config(), {})
    assert "scoring_weights" not in out["config_snapshot"]


def _make_claim(
    needs_corroboration: bool = True,
    needs_review: bool = False,
    corroboration_status: str = "pending",
) -> dict:
    return {
        "claim_id": "abc",
        "claim_type": "prediction",
        "needs_corroboration": needs_corroboration,
        "needs_review": needs_review,
        "corroboration_status": corroboration_status,
    }


def test_build_has_claims_extracted_zero_when_no_claims():
    out = build_run_summary(_minimal_report(), _minimal_config(), {})
    assert out["claims_extracted"] == 0


def test_build_claims_extracted_counts_all_claims():
    items = [
        {"extracted_claims": [_make_claim(), _make_claim()]},
        {"extracted_claims": [_make_claim()]},
    ]
    out = build_run_summary(_minimal_report(items_top_n=items), _minimal_config(), {})
    assert out["claims_extracted"] == 3


def test_build_claims_by_type():
    items = [
        {
            "extracted_claims": [
                _make_claim(),
                {
                    "claim_type": "opinion",
                    "needs_corroboration": False,
                    "needs_review": False,
                    "corroboration_status": "pending",
                },
            ]
        },
    ]
    out = build_run_summary(_minimal_report(items_top_n=items), _minimal_config(), {})
    assert out["claims_by_type"]["prediction"] == 1
    assert out["claims_by_type"]["opinion"] == 1


def test_build_claims_needing_review():
    items = [
        {"extracted_claims": [_make_claim(needs_review=True), _make_claim(needs_review=False)]}
    ]
    out = build_run_summary(_minimal_report(items_top_n=items), _minimal_config(), {})
    assert out["claims_needing_review"] == 1


def test_build_claims_needing_corroboration():
    items = [
        {
            "extracted_claims": [
                _make_claim(needs_corroboration=True),
                _make_claim(needs_corroboration=False),
            ]
        }
    ]
    out = build_run_summary(_minimal_report(items_top_n=items), _minimal_config(), {})
    assert out["claims_needing_corroboration"] == 1


def test_build_corroborated_claims_excludes_pending():
    items = [
        {
            "extracted_claims": [
                _make_claim(corroboration_status="supported"),
                _make_claim(corroboration_status="pending"),
                _make_claim(corroboration_status="refuted"),
            ]
        }
    ]
    out = build_run_summary(_minimal_report(items_top_n=items), _minimal_config(), {})
    assert out["corroborated_claims"] == 2


def test_build_claims_fields_present_with_empty_items():
    out = build_run_summary(_minimal_report(items_top_n=[]), _minimal_config(), {})
    assert "claims_extracted" in out
    assert "claims_by_type" in out
    assert "claims_needing_review" in out
    assert "claims_needing_corroboration" in out
    assert "corroborated_claims" in out


def test_build_claims_skips_non_dict_items():
    items = ["not-a-dict", None, _make_item()]
    out = build_run_summary(_minimal_report(items_top_n=items), _minimal_config(), {})
    assert out["claims_extracted"] == 0
