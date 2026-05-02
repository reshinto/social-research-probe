"""Tests for SQLite schema v1 and migration infrastructure."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from social_research_probe.technologies.persistence.sqlite.schema import (
    SCHEMA_DDL_V1,
    SCHEMA_VERSION,
    ensure_schema,
)


def _in_memory_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


EXPECTED_TABLES = {
    "schema_meta",
    "research_runs",
    "sources",
    "source_snapshots",
    "comments",
    "transcripts",
    "text_surrogates",
    "warnings",
    "artifacts",
}

EXPECTED_INDEXES = {
    "idx_runs_topic",
    "idx_runs_platform",
    "idx_sources_url",
    "idx_snap_run",
    "idx_snap_source",
    "idx_snap_tier",
    "idx_comments_snap",
    "idx_warnings_run",
    "idx_artifacts_run",
    "idx_artifacts_kind",
}


def _table_names(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    return {r[0] for r in rows}


def _index_names(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    return {r[0] for r in rows}


def test_ensure_schema_creates_tables_on_empty_db():
    conn = _in_memory_conn()
    ensure_schema(conn)
    assert _table_names(conn) == EXPECTED_TABLES
    conn.close()


def test_ensure_schema_is_idempotent():
    conn = _in_memory_conn()
    v1 = ensure_schema(conn)
    v2 = ensure_schema(conn)
    assert v1 == v2 == SCHEMA_VERSION
    assert _table_names(conn) == EXPECTED_TABLES
    conn.close()


def test_ensure_schema_records_version():
    conn = _in_memory_conn()
    ensure_schema(conn)
    row = conn.execute("SELECT value FROM schema_meta WHERE key = 'version'").fetchone()
    assert row is not None
    assert int(row[0]) == SCHEMA_VERSION
    conn.close()


def test_ensure_schema_rejects_newer_version():
    conn = _in_memory_conn()
    conn.executescript(SCHEMA_DDL_V1)
    conn.execute(
        "INSERT OR REPLACE INTO schema_meta(key, value) VALUES ('version', ?)",
        (str(SCHEMA_VERSION + 1),),
    )
    conn.commit()
    with pytest.raises(RuntimeError, match="newer than this binary"):
        ensure_schema(conn)
    conn.close()


def test_schema_ddl_creates_indexes():
    conn = _in_memory_conn()
    ensure_schema(conn)
    assert _index_names(conn) >= EXPECTED_INDEXES
    conn.close()


def test_schema_version_constant():
    assert SCHEMA_VERSION == 1


def test_ensure_schema_backs_up_on_version_crossing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    import social_research_probe.technologies.persistence.sqlite.schema as schema_mod

    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys=ON")

    conn.executescript(SCHEMA_DDL_V1)
    conn.execute("INSERT OR REPLACE INTO schema_meta(key, value) VALUES ('version', '1')")
    conn.commit()

    monkeypatch.setattr(schema_mod, "SCHEMA_VERSION", 2)
    monkeypatch.setattr(
        schema_mod,
        "MIGRATIONS",
        [
            schema_mod.MIGRATIONS[0],
            lambda c: None,
        ],
    )

    ensure_schema(conn, db_path=db_path)
    conn.close()

    backups = list(tmp_path.glob("test.db.bak.*"))
    assert len(backups) == 1

    monkeypatch.setattr(schema_mod, "SCHEMA_VERSION", 1)
    monkeypatch.setattr(schema_mod, "MIGRATIONS", schema_mod.MIGRATIONS[:1])


def test_ensure_schema_no_backup_on_fresh_db(tmp_path: Path):
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys=ON")
    ensure_schema(conn, db_path=db_path)
    conn.close()

    backups = list(tmp_path.glob("test.db.bak.*"))
    assert len(backups) == 0
