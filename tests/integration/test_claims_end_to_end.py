"""Integration tests for Phase 5 claim extraction, export, and persistence."""

from __future__ import annotations

import asyncio
import csv
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from social_research_probe.commands._demo_items import build_demo_items
from social_research_probe.config import reset_config_cache
from social_research_probe.platforms.state import PipelineState
from social_research_probe.platforms.youtube.pipeline import YouTubePersistStage
from social_research_probe.technologies.claims import ClaimExtractionTech
from social_research_probe.technologies.persistence.sqlite.connection import open_connection

REQUIRED_CLAIM_TYPES = {
    "fact_claim",
    "opinion",
    "prediction",
    "recommendation",
    "experience",
    "question",
    "objection",
    "pain_point",
    "market_signal",
}

REQUIRED_CLAIM_FIELDS = {
    "claim_id",
    "source_id",
    "claim_text",
    "claim_type",
    "confidence",
    "evidence_layer",
    "evidence_tier",
    "needs_corroboration",
    "corroboration_status",
    "contradiction_status",
    "needs_review",
    "uncertainty",
    "extraction_method",
}


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture()
def isolated_data_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("SRP_DATA_DIR", str(tmp_path))
    reset_config_cache()
    yield tmp_path
    reset_config_cache()


def _cfg_for_db(db_path: Path, enabled: bool = True) -> MagicMock:
    cfg = MagicMock()
    cfg.stage_enabled.return_value = True
    cfg.raw = {
        "database": {
            "enabled": enabled,
            "persist_transcript_text": False,
            "persist_comment_text": True,
        }
    }
    cfg.database_path = db_path
    return cfg


def _state_with_report(report: dict) -> PipelineState:
    state = PipelineState(platform_type="youtube", cmd=None, cache=None, platform_config={})
    state.outputs["report"] = report
    return state


# --- demo items carry extracted_claims ---


def test_demo_items_have_extracted_claims():
    items = build_demo_items()
    for item in items:
        assert "extracted_claims" in item
        assert isinstance(item["extracted_claims"], list)


def test_demo_items_all_claims_have_required_fields():
    items = build_demo_items()
    all_claims = [c for item in items for c in item.get("extracted_claims", [])]
    assert len(all_claims) > 0
    for claim in all_claims:
        missing = REQUIRED_CLAIM_FIELDS - set(claim.keys())
        assert not missing, f"Claim missing fields: {missing}"


def test_demo_items_claims_are_deterministic():
    items_a = build_demo_items()
    items_b = build_demo_items()
    ids_a = [c["claim_id"] for item in items_a for c in item.get("extracted_claims", [])]
    ids_b = [c["claim_id"] for item in items_b for c in item.get("extracted_claims", [])]
    assert ids_a == ids_b


def test_demo_items_claim_types_cover_all_nine():
    items = build_demo_items()
    found = {c["claim_type"] for item in items for c in item.get("extracted_claims", [])}
    assert found == REQUIRED_CLAIM_TYPES


def test_demo_items_extraction_method_is_deterministic():
    items = build_demo_items()
    all_claims = [c for item in items for c in item.get("extracted_claims", [])]
    assert all_claims
    for claim in all_claims:
        assert claim["extraction_method"] == "deterministic"


def test_demo_items_corroboration_status_pending():
    items = build_demo_items()
    all_claims = [c for item in items for c in item.get("extracted_claims", [])]
    for claim in all_claims:
        assert claim["corroboration_status"] == "pending"


def test_demo_items_items_without_primary_text_have_empty_claims():
    items = build_demo_items()
    empty_text_items = [
        item
        for item in items
        if not (item.get("text_surrogate") or {}).get("primary_text", "").strip()
    ]
    for item in empty_text_items:
        assert item["extracted_claims"] == []


# --- claims CSV export ---


def test_demo_report_claims_csv_has_rows(isolated_data_dir):
    import argparse

    from social_research_probe.commands import demo

    demo.run(argparse.Namespace())
    reports_dir = isolated_data_dir / "reports"
    csv_files = list(reports_dir.glob("*-claims.csv"))
    assert csv_files, "No claims CSV found"
    with open(csv_files[0], newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert len(rows) > 0


# --- SQLite claims persistence ---


def test_demo_report_persists_claims_to_db(tmp_path: Path):
    from social_research_probe.commands._demo_fixtures import build_demo_report

    db_path = tmp_path / "srp.db"
    report = build_demo_report()
    report.setdefault("warnings", [])
    report["html_report_path"] = str(tmp_path / "demo_report.html")
    state = _state_with_report(report)

    with patch(
        "social_research_probe.config.load_active_config", return_value=_cfg_for_db(db_path)
    ):
        _run(YouTubePersistStage().execute(state))

    conn = open_connection(db_path)
    try:
        claim_count = conn.execute("SELECT COUNT(*) FROM claims").fetchone()[0]
    finally:
        conn.close()

    assert claim_count >= 1


# --- LLM-backed extraction (mocked) ---

_ALL_EXTRACTED_CLAIM_FIELDS = {
    "claim_id",
    "source_id",
    "source_url",
    "source_title",
    "claim_text",
    "evidence_text",
    "claim_type",
    "entities",
    "confidence",
    "evidence_layer",
    "evidence_tier",
    "needs_corroboration",
    "corroboration_status",
    "contradiction_status",
    "needs_review",
    "uncertainty",
    "extraction_method",
    "source_sentence",
    "position_in_text",
    "context_before",
    "context_after",
    "extracted_at",
}

_ITEM_WITH_TRANSCRIPT = {
    "transcript": "Revenue grew by 42% last year.",
    "url": "https://youtube.com/watch?v=abc",
    "title": "Test Video",
    "id": "abc",
}

_VALID_LLM_RESPONSE = {
    "claims": [
        {
            "claim_text": "Revenue grew by 42% last year.",
            "claim_type": "fact_claim",
            "confidence": 0.9,
            "entities": ["42%"],
            "needs_corroboration": True,
            "uncertainty": "low",
        }
    ]
}


def _mock_cfg_llm(use_llm: bool = True) -> MagicMock:
    cfg = MagicMock()
    cfg.raw = {
        "platforms": {
            "youtube": {
                "claims": {
                    "max_claims_per_source": 10,
                    "max_claim_chars": 500,
                    "use_llm": use_llm,
                }
            }
        }
    }
    return cfg


class TestLLMClaimExtractionIntegration:
    def test_llm_success_path_returns_llm_claims(self) -> None:
        with (
            patch(
                "social_research_probe.technologies.claims.load_active_config",
                return_value=_mock_cfg_llm(use_llm=True),
            ),
            patch(
                "social_research_probe.utils.claims.llm_extractor._run_llm",
                return_value=_VALID_LLM_RESPONSE,
            ),
        ):
            result = _run(ClaimExtractionTech()._execute(_ITEM_WITH_TRANSCRIPT))

        assert len(result) == 1
        claim = result[0]
        assert claim["extraction_method"] == "llm"
        assert claim["claim_type"] == "fact_claim"
        assert claim["claim_text"] == "Revenue grew by 42% last year."
        assert len(claim["claim_id"]) == 16
        missing = _ALL_EXTRACTED_CLAIM_FIELDS - set(claim.keys())
        assert not missing, f"Claim missing fields: {missing}"

    def test_llm_invalid_response_falls_back_to_deterministic(self) -> None:
        with (
            patch(
                "social_research_probe.technologies.claims.load_active_config",
                return_value=_mock_cfg_llm(use_llm=True),
            ),
            patch(
                "social_research_probe.utils.claims.llm_extractor._run_llm",
                return_value={"bad": "no_claims_key"},
            ),
        ):
            result = _run(ClaimExtractionTech()._execute(_ITEM_WITH_TRANSCRIPT))

        assert len(result) >= 1
        assert all(c["extraction_method"] == "deterministic" for c in result)

    def test_llm_exception_falls_back_to_deterministic(self) -> None:
        with (
            patch(
                "social_research_probe.technologies.claims.load_active_config",
                return_value=_mock_cfg_llm(use_llm=True),
            ),
            patch(
                "social_research_probe.utils.claims.llm_extractor._run_llm",
                side_effect=RuntimeError("LLM unavailable"),
            ),
        ):
            result = _run(ClaimExtractionTech()._execute(_ITEM_WITH_TRANSCRIPT))

        assert len(result) >= 1
        assert all(c["extraction_method"] == "deterministic" for c in result)

    def test_deterministic_default_llm_never_called(self) -> None:
        mock_run_llm = MagicMock()
        with (
            patch(
                "social_research_probe.technologies.claims.load_active_config",
                return_value=_mock_cfg_llm(use_llm=False),
            ),
            patch(
                "social_research_probe.utils.claims.llm_extractor._run_llm",
                mock_run_llm,
            ),
        ):
            result = _run(ClaimExtractionTech()._execute(_ITEM_WITH_TRANSCRIPT))

        assert len(result) >= 1
        assert all(c["extraction_method"] == "deterministic" for c in result)
        mock_run_llm.assert_not_called()
