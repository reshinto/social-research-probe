"""Tests for Phase 3 sources CSV builder."""

from __future__ import annotations

import csv
from pathlib import Path

from social_research_probe.technologies.report_render.export.sources_csv import (
    SOURCES_COLUMNS,
    build_sources_rows,
    write_sources_csv,
)


def _make_item(**kwargs) -> dict:
    return kwargs


def _make_full_item(title: str = "Title", channel: str = "Chan") -> dict:
    return {
        "title": title,
        "channel": channel,
        "url": "https://example.com",
        "source_class": "primary",
        "scores": {"trust": 0.8, "trend": 0.6, "opportunity": 0.4, "overall": 0.7},
        "evidence_tier": "metadata_transcript",
        "transcript_status": "available",
        "comments_status": "available",
        "corroboration_verdict": "verified",
        "one_line_takeaway": "Good video",
    }


def test_build_rows_basic():
    items = [_make_full_item("A"), _make_full_item("B")]
    rows = build_sources_rows(items)
    assert len(rows) == 2
    for row in rows:
        assert set(row.keys()) == set(SOURCES_COLUMNS)


def test_build_rows_extracts_scores():
    item = _make_full_item()
    rows = build_sources_rows([item])
    assert rows[0]["trust"] == 0.8
    assert rows[0]["trend"] == 0.6
    assert rows[0]["opportunity"] == 0.4
    assert rows[0]["overall"] == 0.7


def test_build_rows_rank_one_indexed():
    items = [_make_full_item("A"), _make_full_item("B")]
    rows = build_sources_rows(items)
    assert rows[0]["rank"] == 1
    assert rows[1]["rank"] == 2


def test_build_rows_missing_fields_default():
    rows = build_sources_rows([{}])
    assert len(rows) == 1
    row = rows[0]
    assert row["title"] == ""
    assert row["trust"] == ""
    assert row["evidence_tier"] == ""
    assert row["rank"] == 1


def test_build_rows_empty_list():
    assert build_sources_rows([]) == []


def test_write_csv_creates_file(tmp_path: Path):
    rows = build_sources_rows([_make_full_item()])
    out = tmp_path / "sources.csv"
    write_sources_csv(rows, out)
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    for col in SOURCES_COLUMNS:
        assert col in content


def test_write_csv_roundtrip(tmp_path: Path):
    item = _make_full_item("Roundtrip", "Chan2")
    rows = build_sources_rows([item])
    out = tmp_path / "sources.csv"
    write_sources_csv(rows, out)
    with out.open(encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
    assert len(reader) == 1
    assert reader[0]["title"] == "Roundtrip"
    assert reader[0]["channel"] == "Chan2"
    assert reader[0]["trust"] == "0.8"


def test_write_csv_handles_unicode(tmp_path: Path):
    item = _make_full_item(title="日本語テスト")
    rows = build_sources_rows([item])
    out = tmp_path / "sources.csv"
    write_sources_csv(rows, out)
    with out.open(encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
    assert reader[0]["title"] == "日本語テスト"


def test_write_csv_handles_commas_in_text(tmp_path: Path):
    item = _make_full_item()
    item["one_line_takeaway"] = "foo, bar, baz"
    rows = build_sources_rows([item])
    out = tmp_path / "sources.csv"
    write_sources_csv(rows, out)
    with out.open(encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
    assert reader[0]["one_line_takeaway"] == "foo, bar, baz"


def test_write_csv_headers_only_when_empty(tmp_path: Path):
    out = tmp_path / "sources.csv"
    write_sources_csv([], out)
    assert out.exists()
    with out.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == SOURCES_COLUMNS
        rows = list(reader)
    assert rows == []
