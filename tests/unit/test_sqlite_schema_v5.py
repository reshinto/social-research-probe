"""Tests for Schema V5: local watches and alert events."""

from __future__ import annotations

import sqlite3

from social_research_probe.technologies.persistence.sqlite.schema import (
    SCHEMA_DDL_V1,
    SCHEMA_DDL_V2,
    SCHEMA_DDL_V3,
    SCHEMA_DDL_V4,
    SCHEMA_DDL_V5,
    SCHEMA_VERSION,
    ensure_schema,
)


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ?", (name,)
    ).fetchone()
    return row is not None


def test_schema_version_is_6() -> None:
    assert SCHEMA_VERSION == 6


def test_fresh_schema_creates_watch_tables() -> None:
    conn = _conn()
    ensure_schema(conn)
    assert _table_exists(conn, "watches")
    assert _table_exists(conn, "watch_runs")
    assert _table_exists(conn, "alert_events")
    assert _table_exists(conn, "notification_deliveries")
    conn.close()


def test_v4_to_v5_migration_preserves_runs() -> None:
    conn = _conn()
    conn.executescript(SCHEMA_DDL_V1)
    conn.executescript(SCHEMA_DDL_V2)
    conn.executescript(SCHEMA_DDL_V3)
    conn.executescript(SCHEMA_DDL_V4)
    conn.execute("INSERT OR REPLACE INTO schema_meta(key, value) VALUES ('version', '4')")
    conn.execute(
        "INSERT INTO research_runs (run_id, topic, platform, started_at, schema_version) "
        "VALUES ('run-1', 'AI', 'youtube', '2026-01-01', 4)"
    )
    conn.commit()
    ensure_schema(conn)
    assert _table_exists(conn, "watches")
    assert (
        conn.execute("SELECT topic FROM research_runs WHERE run_id='run-1'").fetchone()[0] == "AI"
    )
    conn.close()


def test_v5_to_v6_migration_preserves_alerts() -> None:
    conn = _conn()
    conn.executescript(SCHEMA_DDL_V1)
    conn.executescript(SCHEMA_DDL_V2)
    conn.executescript(SCHEMA_DDL_V3)
    conn.executescript(SCHEMA_DDL_V4)
    conn.executescript(SCHEMA_DDL_V5)
    conn.execute("INSERT OR REPLACE INTO schema_meta(key, value) VALUES ('version', '5')")
    conn.execute(
        """
        INSERT INTO watches (watch_id, topic, platform, created_at, updated_at)
        VALUES ('watch-1', 'AI', 'youtube', '2026-01-01', '2026-01-01')
        """
    )
    conn.execute(
        """
        INSERT INTO alert_events (alert_id, watch_id, created_at)
        VALUES ('alert-1', 'watch-1', '2026-01-01')
        """
    )
    conn.commit()
    ensure_schema(conn)
    assert _table_exists(conn, "notification_deliveries")
    assert conn.execute("SELECT watch_id FROM alert_events").fetchone()[0] == "watch-1"
    conn.close()
