"""Tests for SQLite schema V3: claim_reviews and claim_notes tables."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

import pytest

from social_research_probe.technologies.persistence.sqlite.schema import (
    SCHEMA_DDL_V1,
    SCHEMA_DDL_V2,
    SCHEMA_VERSION,
    ensure_schema,
)


@contextmanager
def _in_memory_conn() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
    finally:
        conn.close()


def _table_names(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    return {r[0] for r in rows}


def _seed_v2_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_DDL_V1)
    conn.executescript(SCHEMA_DDL_V2)
    conn.execute("INSERT OR REPLACE INTO schema_meta(key, value) VALUES ('version', '2')")
    conn.commit()


def _insert_run(conn: sqlite3.Connection) -> int:
    conn.execute(
        "INSERT INTO research_runs(run_id, topic, platform, started_at, schema_version) "
        "VALUES ('r1', 'test', 'youtube', '2026-01-01T00:00:00', 3)"
    )
    conn.commit()
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def _insert_source(conn: sqlite3.Connection) -> int:
    conn.execute(
        "INSERT INTO sources(platform, external_id, url, first_seen_at, last_seen_at) "
        "VALUES ('youtube', 'vid1', 'https://y.com/1', '2026-01-01', '2026-01-01')"
    )
    conn.commit()
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def _insert_snapshot(conn: sqlite3.Connection, source_id: int, run_id: int) -> int:
    conn.execute(
        "INSERT INTO source_snapshots(source_id, run_id, observed_at) VALUES (?, ?, '2026-01-01')",
        (source_id, run_id),
    )
    conn.commit()
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def _insert_claim(conn: sqlite3.Connection, run_id: int, snap_id: int) -> int:
    conn.execute(
        "INSERT INTO claims(claim_id, run_id, source_snapshot_id, claim_text, created_at) "
        "VALUES ('c1', ?, ?, 'test claim', '2026-01-01')",
        (run_id, snap_id),
    )
    conn.commit()
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def test_schema_version_is_3():
    assert SCHEMA_VERSION == 3


def test_fresh_ensure_schema_creates_review_and_notes_tables():
    with _in_memory_conn() as conn:
        ensure_schema(conn)
        tables = _table_names(conn)
        assert "claim_reviews" in tables
        assert "claim_notes" in tables


def test_v2_to_v3_migration_creates_tables():
    with _in_memory_conn() as conn:
        _seed_v2_db(conn)
        tables_before = _table_names(conn)
        assert "claim_reviews" not in tables_before

        ensure_schema(conn)

        tables_after = _table_names(conn)
        assert "claim_reviews" in tables_after
        assert "claim_notes" in tables_after


def test_v2_to_v3_migration_preserves_existing_claim_rows():
    with _in_memory_conn() as conn:
        _seed_v2_db(conn)
        run_id = _insert_run(conn)
        source_id = _insert_source(conn)
        snap_id = _insert_snapshot(conn, source_id, run_id)
        claim_pk = _insert_claim(conn, run_id, snap_id)

        ensure_schema(conn)

        claim = conn.execute(
            "SELECT id, claim_id, claim_text FROM claims WHERE id = ?", (claim_pk,)
        ).fetchone()
        assert claim == (claim_pk, "c1", "test claim")
        tables = _table_names(conn)
        assert "claim_reviews" in tables
        assert "claim_notes" in tables


def test_claim_reviews_unique_claim_pk_enforced():
    with _in_memory_conn() as conn:
        ensure_schema(conn)
        run_id = _insert_run(conn)
        source_id = _insert_source(conn)
        snap_id = _insert_snapshot(conn, source_id, run_id)
        claim_pk = _insert_claim(conn, run_id, snap_id)

        conn.execute(
            "INSERT INTO claim_reviews(claim_pk, claim_id, run_id, reviewed_at) "
            "VALUES (?, 'c1', ?, '2026-01-01T00:00:00')",
            (claim_pk, run_id),
        )
        conn.commit()

        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO claim_reviews(claim_pk, claim_id, run_id, reviewed_at) "
                "VALUES (?, 'c1', ?, '2026-01-02T00:00:00')",
                (claim_pk, run_id),
            )


def test_claim_notes_allows_multiple_per_claim():
    with _in_memory_conn() as conn:
        ensure_schema(conn)
        run_id = _insert_run(conn)
        source_id = _insert_source(conn)
        snap_id = _insert_snapshot(conn, source_id, run_id)
        claim_pk = _insert_claim(conn, run_id, snap_id)

        conn.execute(
            "INSERT INTO claim_notes(claim_pk, claim_id, note_text, created_at) "
            "VALUES (?, 'c1', 'note 1', '2026-01-01')",
            (claim_pk,),
        )
        conn.execute(
            "INSERT INTO claim_notes(claim_pk, claim_id, note_text, created_at) "
            "VALUES (?, 'c1', 'note 2', '2026-01-02')",
            (claim_pk,),
        )
        conn.commit()

        count = conn.execute(
            "SELECT COUNT(*) FROM claim_notes WHERE claim_pk = ?", (claim_pk,)
        ).fetchone()[0]
        assert count == 2


def test_fk_cascade_deleting_claim_removes_reviews_and_notes():
    with _in_memory_conn() as conn:
        ensure_schema(conn)
        run_id = _insert_run(conn)
        source_id = _insert_source(conn)
        snap_id = _insert_snapshot(conn, source_id, run_id)
        claim_pk = _insert_claim(conn, run_id, snap_id)

        conn.execute(
            "INSERT INTO claim_reviews(claim_pk, claim_id, run_id, reviewed_at) "
            "VALUES (?, 'c1', ?, '2026-01-01T00:00:00')",
            (claim_pk, run_id),
        )
        conn.execute(
            "INSERT INTO claim_notes(claim_pk, claim_id, note_text, created_at) "
            "VALUES (?, 'c1', 'note', '2026-01-01')",
            (claim_pk,),
        )
        conn.commit()

        conn.execute("DELETE FROM claims WHERE id = ?", (claim_pk,))
        conn.commit()

        review_count = conn.execute("SELECT COUNT(*) FROM claim_reviews").fetchone()[0]
        note_count = conn.execute("SELECT COUNT(*) FROM claim_notes").fetchone()[0]
        assert review_count == 0
        assert note_count == 0
