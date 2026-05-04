"""Tests for Schema V4: narrative_clusters, narrative_claims, narrative_sources."""

from __future__ import annotations

import sqlite3

from social_research_probe.technologies.persistence.sqlite.schema import (
    MIGRATIONS,
    SCHEMA_DDL_V1,
    SCHEMA_DDL_V2,
    SCHEMA_DDL_V3,
    SCHEMA_DDL_V4,
    SCHEMA_VERSION,
    ensure_schema,
)


def _fresh_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()
    return row is not None


class TestSchemaV4Constants:
    def test_current_schema_version_is_5(self) -> None:
        assert SCHEMA_VERSION == 5

    def test_migrations_list_has_5_entries(self) -> None:
        assert len(MIGRATIONS) == 5

    def test_ddl_v4_defined(self) -> None:
        assert "narrative_clusters" in SCHEMA_DDL_V4
        assert "narrative_claims" in SCHEMA_DDL_V4
        assert "narrative_sources" in SCHEMA_DDL_V4


class TestFreshSchema:
    def test_fresh_creates_narrative_tables(self) -> None:
        conn = _fresh_db()
        ensure_schema(conn)
        assert _table_exists(conn, "narrative_clusters")
        assert _table_exists(conn, "narrative_claims")
        assert _table_exists(conn, "narrative_sources")
        conn.close()

    def test_fresh_schema_version_stored(self) -> None:
        conn = _fresh_db()
        ensure_schema(conn)
        row = conn.execute("SELECT value FROM schema_meta WHERE key = 'version'").fetchone()
        assert int(row[0]) == 5
        conn.close()


class TestMigrationV3ToV4:
    def _v3_db(self) -> sqlite3.Connection:
        conn = _fresh_db()
        conn.executescript(SCHEMA_DDL_V1)
        conn.executescript(SCHEMA_DDL_V2)
        conn.executescript(SCHEMA_DDL_V3)
        conn.execute("INSERT OR REPLACE INTO schema_meta(key, value) VALUES ('version', '3')")
        conn.commit()
        return conn

    def test_v3_to_v4_creates_tables(self) -> None:
        conn = self._v3_db()
        assert not _table_exists(conn, "narrative_clusters")
        ensure_schema(conn)
        assert _table_exists(conn, "narrative_clusters")
        assert _table_exists(conn, "narrative_claims")
        assert _table_exists(conn, "narrative_sources")
        conn.close()

    def test_v3_to_v4_preserves_existing_data(self) -> None:
        conn = self._v3_db()
        conn.execute(
            "INSERT INTO research_runs (run_id, topic, platform, started_at, schema_version) "
            "VALUES ('r1', 'test', 'youtube', '2024-01-01', 3)"
        )
        conn.commit()
        ensure_schema(conn)
        row = conn.execute("SELECT topic FROM research_runs WHERE run_id = 'r1'").fetchone()
        assert row[0] == "test"
        conn.close()

    def test_unique_constraint_on_narrative_clusters(self) -> None:
        conn = _fresh_db()
        ensure_schema(conn)
        conn.execute(
            "INSERT INTO research_runs (run_id, topic, platform, started_at, schema_version) "
            "VALUES ('r1', 'test', 'youtube', '2024-01-01', 4)"
        )
        run_pk = conn.execute("SELECT id FROM research_runs WHERE run_id = 'r1'").fetchone()[0]
        conn.execute(
            "INSERT INTO narrative_clusters (narrative_id, run_id, title, cluster_type, created_at) "
            "VALUES ('n1', ?, 'title', 'theme', '2024-01-01')",
            (run_pk,),
        )
        try:
            conn.execute(
                "INSERT INTO narrative_clusters (narrative_id, run_id, title, cluster_type, created_at) "
                "VALUES ('n1', ?, 'title2', 'risk', '2024-01-01')",
                (run_pk,),
            )
            raise AssertionError("Expected IntegrityError")
        except sqlite3.IntegrityError:
            pass
        conn.close()

    def test_fk_cascade_on_delete(self) -> None:
        conn = _fresh_db()
        ensure_schema(conn)
        conn.execute(
            "INSERT INTO research_runs (run_id, topic, platform, started_at, schema_version) "
            "VALUES ('r1', 'test', 'youtube', '2024-01-01', 4)"
        )
        run_pk = conn.execute("SELECT id FROM research_runs WHERE run_id = 'r1'").fetchone()[0]
        conn.execute(
            "INSERT INTO narrative_clusters (narrative_id, run_id, title, cluster_type, created_at) "
            "VALUES ('n1', ?, 'title', 'theme', '2024-01-01')",
            (run_pk,),
        )
        narr_pk = conn.execute("SELECT id FROM narrative_clusters").fetchone()[0]
        conn.execute(
            "INSERT INTO narrative_claims (narrative_pk, claim_id) VALUES (?, 'c1')",
            (narr_pk,),
        )
        conn.execute(
            "INSERT INTO narrative_sources (narrative_pk, source_id, source_url) VALUES (?, 's1', 'http://x')",
            (narr_pk,),
        )
        conn.execute("DELETE FROM narrative_clusters WHERE id = ?", (narr_pk,))
        assert conn.execute("SELECT COUNT(*) FROM narrative_claims").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM narrative_sources").fetchone()[0] == 0
        conn.close()
