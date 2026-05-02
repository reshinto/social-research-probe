"""Tests for SQLite connection factory."""

from __future__ import annotations

from pathlib import Path

from social_research_probe.technologies.persistence.sqlite.connection import (
    open_connection,
)


def test_open_connection_creates_parent_dir(tmp_path: Path):
    nested = tmp_path / "a" / "b" / "test.db"
    conn = open_connection(nested)
    assert nested.parent.exists()
    conn.close()


def test_open_connection_sets_foreign_keys(tmp_path: Path):
    db_path = tmp_path / "test.db"
    conn = open_connection(db_path)
    row = conn.execute("PRAGMA foreign_keys").fetchone()
    assert row[0] == 1
    conn.close()


def test_open_connection_sets_wal(tmp_path: Path):
    db_path = tmp_path / "test.db"
    conn = open_connection(db_path)
    row = conn.execute("PRAGMA journal_mode").fetchone()
    assert row[0] == "wal"
    conn.close()


def test_open_connection_sets_synchronous_normal(tmp_path: Path):
    db_path = tmp_path / "test.db"
    conn = open_connection(db_path)
    row = conn.execute("PRAGMA synchronous").fetchone()
    assert row[0] == 1  # NORMAL = 1
    conn.close()


def test_open_connection_creates_valid_db(tmp_path: Path):
    db_path = tmp_path / "test.db"
    conn = open_connection(db_path)
    conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY)")
    conn.execute("INSERT INTO t VALUES (1)")
    conn.commit()
    row = conn.execute("SELECT id FROM t").fetchone()
    assert row[0] == 1
    conn.close()
