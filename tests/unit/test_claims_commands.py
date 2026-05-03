"""Tests for claims CLI command handlers."""

from __future__ import annotations

import argparse
import json
import sqlite3
from unittest.mock import patch

import pytest

from social_research_probe.commands.claims import run
from social_research_probe.technologies.persistence.sqlite.schema import ensure_schema


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys=ON")
    ensure_schema(conn)
    return conn


def _seed(conn: sqlite3.Connection) -> int:
    """Seed DB with run, source, snapshot, claims. Returns run_pk."""
    conn.execute(
        "INSERT INTO research_runs(run_id, topic, platform, started_at, schema_version) "
        "VALUES ('r1', 'AI safety', 'youtube', '2026-01-01T00:00:00', 3)"
    )
    run_pk = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute(
        "INSERT INTO sources(platform, external_id, url, first_seen_at, last_seen_at) "
        "VALUES ('youtube', 'vid1', 'https://y.com/1', '2026-01-01', '2026-01-01')"
    )
    source_pk = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute(
        "INSERT INTO source_snapshots(source_id, run_id, observed_at) VALUES (?, ?, '2026-01-01')",
        (source_pk, run_pk),
    )
    snap_pk = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute(
        "INSERT INTO claims(claim_id, run_id, source_snapshot_id, source_id, "
        "source_url, source_title, claim_text, claim_type, extraction_method, "
        "needs_review, needs_corroboration, corroboration_status, position_in_text, created_at) "
        "VALUES ('c1', ?, ?, ?, 'https://y.com/1', 'Video', 'test claim', "
        "'fact_claim', 'deterministic', 1, 1, 'pending', 10, '2026-01-01')",
        (run_pk, snap_pk, source_pk),
    )
    conn.commit()
    return run_pk


def _make_args(**kwargs) -> argparse.Namespace:
    defaults = {
        "command": "claims",
        "claims_cmd": None,
        "_claims_parser": None,
        "output": "json",
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


class _MockConfig:
    def __init__(self, db_path):
        self.database_path = db_path


@pytest.fixture()
def seeded_db(tmp_path):
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys=ON")
    ensure_schema(conn, db_path)
    _seed(conn)
    conn.close()
    return db_path


def _run_cmd(args, db_path, capsys):
    with patch(
        "social_research_probe.config.load_active_config",
        return_value=_MockConfig(db_path),
    ):
        result = run(args)
    captured = capsys.readouterr()
    return result, captured.out


class TestDispatch:
    def test_no_subcommand_with_parser_prints_help(self, capsys):
        mock_parser = argparse.ArgumentParser(prog="srp claims")
        args = _make_args(_claims_parser=mock_parser)
        result = run(args)
        assert result == 0
        out = capsys.readouterr().out
        assert "srp claims" in out

    def test_unknown_subcommand_returns_error(self):
        args = _make_args(claims_cmd="unknown-action")
        result = run(args)
        assert result == 1

    def test_no_subcommand_no_parser_returns_zero(self, capsys):
        args = _make_args()  # claims_cmd=None, _claims_parser=None
        result = run(args)
        assert result == 0
        assert capsys.readouterr().out == ""


class TestList:
    def test_returns_claims(self, seeded_db, capsys):
        args = _make_args(
            claims_cmd="list",
            run_id=None,
            topic=None,
            claim_type=None,
            needs_review=False,
            needs_corroboration=False,
            corroboration_status=None,
            extraction_method=None,
            limit=100,
        )
        result, out = _run_cmd(args, seeded_db, capsys)
        assert result == 0
        data = json.loads(out)
        assert len(data) == 1
        assert data[0]["claim_id"] == "c1"

    def test_filter_by_topic(self, seeded_db, capsys):
        args = _make_args(
            claims_cmd="list",
            run_id=None,
            topic="nonexistent",
            claim_type=None,
            needs_review=False,
            needs_corroboration=False,
            corroboration_status=None,
            extraction_method=None,
            limit=100,
        )
        result, out = _run_cmd(args, seeded_db, capsys)
        assert result == 0
        data = json.loads(out)
        assert len(data) == 0

    def test_filter_needs_review(self, seeded_db, capsys):
        args = _make_args(
            claims_cmd="list",
            run_id=None,
            topic=None,
            claim_type=None,
            needs_review=True,
            needs_corroboration=False,
            corroboration_status=None,
            extraction_method=None,
            limit=100,
        )
        result, out = _run_cmd(args, seeded_db, capsys)
        assert result == 0
        data = json.loads(out)
        assert len(data) == 1


class TestShow:
    def test_displays_claim(self, seeded_db, capsys):
        args = _make_args(claims_cmd="show", claim_id="c1")
        result, out = _run_cmd(args, seeded_db, capsys)
        assert result == 0
        data = json.loads(out)
        assert data["claim_id"] == "c1"
        assert "reviews" in data
        assert "notes" in data

    def test_nonexistent_claim(self, seeded_db, capsys):
        args = _make_args(claims_cmd="show", claim_id="nonexistent")
        result, out = _run_cmd(args, seeded_db, capsys)
        assert result == 1
        data = json.loads(out)
        assert "error" in data


class TestStats:
    def test_correct_counts(self, seeded_db, capsys):
        args = _make_args(claims_cmd="stats")
        result, out = _run_cmd(args, seeded_db, capsys)
        assert result == 0
        data = json.loads(out)
        assert data["total"] == 1
        assert data["by_type"]["fact_claim"] == 1
        assert data["needs_review"] == 1


class TestReview:
    def test_writes_review(self, seeded_db, capsys):
        args = _make_args(
            claims_cmd="review",
            claim_id="c1",
            status="verified",
            importance=None,
            notes="looks good",
        )
        result, out = _run_cmd(args, seeded_db, capsys)
        assert result == 0
        data = json.loads(out)
        assert data["ok"] is True

        conn = sqlite3.connect(str(seeded_db))
        try:
            quality_score = conn.execute(
                "SELECT quality_score FROM claim_reviews WHERE claim_id = 'c1'"
            ).fetchone()[0]
        finally:
            conn.close()
        assert quality_score is not None
        assert 0.0 <= quality_score <= 1.0

    def test_invalid_status(self, seeded_db, capsys):
        args = _make_args(
            claims_cmd="review",
            claim_id="c1",
            status="banana",
            importance=None,
            notes="",
        )
        result, out = _run_cmd(args, seeded_db, capsys)
        assert result == 1
        data = json.loads(out)
        assert "error" in data

    def test_with_importance(self, seeded_db, capsys):
        args = _make_args(
            claims_cmd="review",
            claim_id="c1",
            status="verified",
            importance="high",
            notes="",
        )
        result, _out = _run_cmd(args, seeded_db, capsys)
        assert result == 0


class TestNote:
    def test_appends_note(self, seeded_db, capsys):
        args = _make_args(claims_cmd="note", claim_id="c1", text="important finding")
        result, out = _run_cmd(args, seeded_db, capsys)
        assert result == 0
        data = json.loads(out)
        assert data["ok"] is True
        assert data["note"] == "important finding"

    def test_rejects_whitespace_note(self, seeded_db, capsys):
        args = _make_args(claims_cmd="note", claim_id="c1", text="   ")
        result, out = _run_cmd(args, seeded_db, capsys)
        assert result == 1
        data = json.loads(out)
        assert "error" in data

        conn = sqlite3.connect(str(seeded_db))
        try:
            count = conn.execute("SELECT COUNT(*) FROM claim_notes").fetchone()[0]
        finally:
            conn.close()
        assert count == 0


class TestReviewEdgeCases:
    def test_invalid_importance(self, seeded_db, capsys):
        args = _make_args(
            claims_cmd="review",
            claim_id="c1",
            status="verified",
            importance="banana",
            notes="",
        )
        result, out = _run_cmd(args, seeded_db, capsys)
        assert result == 1
        data = json.loads(out)
        assert "error" in data

    def test_claim_not_found_in_review(self, seeded_db, capsys):
        args = _make_args(
            claims_cmd="review",
            claim_id="nonexistent",
            status="verified",
            importance=None,
            notes="",
        )
        result, _out = _run_cmd(args, seeded_db, capsys)
        assert result == 1

    def test_claim_not_found_in_note(self, seeded_db, capsys):
        args = _make_args(claims_cmd="note", claim_id="nonexistent", text="note")
        result, _out = _run_cmd(args, seeded_db, capsys)
        assert result == 1


class TestEmptyDB:
    def test_list_empty(self, tmp_path, capsys):
        db_path = tmp_path / "empty.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("PRAGMA foreign_keys=ON")
        ensure_schema(conn, db_path)
        conn.close()
        args = _make_args(
            claims_cmd="list",
            run_id=None,
            topic=None,
            claim_type=None,
            needs_review=False,
            needs_corroboration=False,
            corroboration_status=None,
            extraction_method=None,
            limit=100,
        )
        result, out = _run_cmd(args, db_path, capsys)
        assert result == 0
        data = json.loads(out)
        assert data == []

    def test_stats_empty(self, tmp_path, capsys):
        db_path = tmp_path / "empty.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("PRAGMA foreign_keys=ON")
        ensure_schema(conn, db_path)
        conn.close()
        args = _make_args(claims_cmd="stats")
        result, out = _run_cmd(args, db_path, capsys)
        assert result == 0
        data = json.loads(out)
        assert data["total"] == 0
