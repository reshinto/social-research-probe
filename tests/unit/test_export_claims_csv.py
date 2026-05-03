"""Tests for Phase 5 claims CSV builder."""

from __future__ import annotations

import csv
import io
from pathlib import Path

from social_research_probe.technologies.report_render.export.claims_csv import (
    CLAIMS_COLUMNS,
    build_claims_rows,
    write_claims_csv,
)


def _sample_claim(**overrides) -> dict:
    base = {
        "claim_id": "abc123abc123abcd",
        "source_id": "vid1",
        "source_url": "https://youtube.com/watch?v=vid1",
        "source_title": "Test Video",
        "claim_text": "AI will replace 50% of jobs.",
        "claim_type": "prediction",
        "evidence_text": "surrounding paragraph",
        "entities": ["AI", "50%"],
        "confidence": 0.7,
        "evidence_layer": "transcript",
        "evidence_tier": "transcript_rich",
        "needs_corroboration": True,
        "corroboration_status": "pending",
        "contradiction_status": "none",
        "needs_review": False,
        "uncertainty": "low",
        "extraction_method": "deterministic",
    }
    return {**base, **overrides}


def _sample_item(claims: list | None = None) -> dict:
    return {
        "id": "vid1",
        "title": "Test Video",
        "extracted_claims": claims if claims is not None else [_sample_claim()],
    }


class TestBuildClaimsRows:
    def test_normal_case_one_claim_per_item(self) -> None:
        items = [_sample_item()]
        rows = build_claims_rows(items)
        assert len(rows) == 1
        assert rows[0]["claim_id"] == "abc123abc123abcd"
        assert rows[0]["claim_type"] == "prediction"

    def test_multiple_claims_across_items(self) -> None:
        items = [
            _sample_item([_sample_claim(claim_id="id1"), _sample_claim(claim_id="id2")]),
            _sample_item([_sample_claim(claim_id="id3")]),
        ]
        rows = build_claims_rows(items)
        assert len(rows) == 3

    def test_empty_items_list(self) -> None:
        assert build_claims_rows([]) == []

    def test_item_without_extracted_claims(self) -> None:
        rows = build_claims_rows([{"id": "vid1", "title": "T"}])
        assert rows == []

    def test_item_with_none_extracted_claims(self) -> None:
        rows = build_claims_rows([{"id": "vid1", "extracted_claims": None}])
        assert rows == []

    def test_non_dict_item_skipped(self) -> None:
        rows = build_claims_rows(["not-a-dict", 42])
        assert rows == []

    def test_non_dict_claim_skipped(self) -> None:
        item = {"extracted_claims": ["bad", _sample_claim()]}
        rows = build_claims_rows([item])
        assert len(rows) == 1

    def test_entities_joined_with_semicolon(self) -> None:
        rows = build_claims_rows([_sample_item([_sample_claim(entities=["AI", "OpenAI", "50%"])])])
        assert rows[0]["entities"] == "AI; OpenAI; 50%"

    def test_empty_entities_produces_empty_string(self) -> None:
        rows = build_claims_rows([_sample_item([_sample_claim(entities=[])])])
        assert rows[0]["entities"] == ""

    def test_missing_entities_key_produces_empty_string(self) -> None:
        claim = {k: v for k, v in _sample_claim().items() if k != "entities"}
        rows = build_claims_rows([_sample_item([claim])])
        assert rows[0]["entities"] == ""

    def test_row_has_all_17_columns(self) -> None:
        rows = build_claims_rows([_sample_item()])
        assert set(rows[0].keys()) == set(CLAIMS_COLUMNS)


class TestWriteClaimsCsv:
    def test_writes_headers_only_for_empty_rows(self, tmp_path: Path) -> None:
        path = tmp_path / "claims.csv"
        write_claims_csv([], path)
        assert path.exists()
        content = path.read_text(encoding="utf-8")
        reader = csv.DictReader(io.StringIO(content))
        assert reader.fieldnames == CLAIMS_COLUMNS
        rows = list(reader)
        assert rows == []

    def test_csv_roundtrip(self, tmp_path: Path) -> None:
        rows = build_claims_rows([_sample_item()])
        path = tmp_path / "claims.csv"
        write_claims_csv(rows, path)
        content = path.read_text(encoding="utf-8")
        reader = csv.DictReader(io.StringIO(content))
        written = list(reader)
        assert len(written) == 1
        assert written[0]["claim_id"] == "abc123abc123abcd"
        assert written[0]["claim_type"] == "prediction"

    def test_creates_parent_directory(self, tmp_path: Path) -> None:
        path = tmp_path / "subdir" / "claims.csv"
        write_claims_csv([], path)
        assert path.exists()

    def test_returns_path(self, tmp_path: Path) -> None:
        path = tmp_path / "claims.csv"
        result = write_claims_csv([], path)
        assert result == path
