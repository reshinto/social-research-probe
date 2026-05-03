"""Tests for SQLite claims table: schema v2, insert_claims, and persistence integration."""

from __future__ import annotations

import json
import sqlite3

from social_research_probe.technologies.persistence.sqlite.repository import insert_claims
from social_research_probe.technologies.persistence.sqlite.schema import (
    SCHEMA_DDL_V1,
    SCHEMA_VERSION,
    ensure_schema,
)


def _in_memory_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _full_schema_conn() -> sqlite3.Connection:
    conn = _in_memory_conn()
    ensure_schema(conn)
    return conn


def _insert_run(conn: sqlite3.Connection) -> int:
    cur = conn.execute(
        """
        INSERT INTO research_runs (
            run_id, topic, platform, started_at,
            export_paths_json, warning_count, exit_status,
            config_snapshot_json, schema_version
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("run-1", "ai", "youtube", "2024-01-01T00:00:00", "{}", 0, "ok", "{}", SCHEMA_VERSION),
    )
    return cur.lastrowid  # type: ignore[return-value]


def _insert_source(conn: sqlite3.Connection) -> int:
    cur = conn.execute(
        """
        INSERT INTO sources (platform, external_id, url, first_seen_at, last_seen_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("youtube", "vid1", "https://youtube.com/watch?v=vid1", "2024-01-01", "2024-01-01"),
    )
    return cur.lastrowid  # type: ignore[return-value]


def _insert_snapshot(conn: sqlite3.Connection, source_pk: int, run_pk: int) -> int:
    cur = conn.execute(
        """
        INSERT INTO source_snapshots (source_id, run_id, observed_at)
        VALUES (?, ?, ?)
        """,
        (source_pk, run_pk, "2024-01-01T00:00:00"),
    )
    return cur.lastrowid  # type: ignore[return-value]


def _sample_claim(claim_id: str = "abc123abc123abcd") -> dict:
    return {
        "claim_id": claim_id,
        "claim_text": "AI will replace 50% of jobs.",
        "evidence_text": "surrounding paragraph",
        "claim_type": "prediction",
        "entities": ["AI"],
        "confidence": 0.7,
        "evidence_layer": "transcript",
        "evidence_tier": "transcript_rich",
        "needs_corroboration": True,
        "corroboration_status": "pending",
        "contradiction_status": "none",
        "needs_review": False,
        "uncertainty": "low",
        "extraction_method": "deterministic",
        "source_sentence": "AI will replace 50% of jobs.",
        "position_in_text": 0,
        "context_before": "",
        "context_after": " This is significant.",
        "extracted_at": "2024-01-01T00:00:00",
    }


class TestFreshSchema:
    def test_fresh_schema_has_claims_table(self) -> None:
        conn = _full_schema_conn()
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='claims'"
        ).fetchall()
        assert len(rows) == 1

    def test_fresh_schema_has_all_claim_indexes(self) -> None:
        conn = _full_schema_conn()
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_claims_%'"
        ).fetchall()
        index_names = {r[0] for r in rows}
        assert index_names == {
            "idx_claims_run",
            "idx_claims_source",
            "idx_claims_type",
            "idx_claims_review",
            "idx_claims_corrob",
        }


class TestSchemaMigration:
    def test_v1_to_v2_migration_creates_claims_table(self) -> None:
        conn = _in_memory_conn()
        conn.executescript(SCHEMA_DDL_V1)
        conn.execute("INSERT OR REPLACE INTO schema_meta(key, value) VALUES ('version', '1')")
        conn.commit()

        ensure_schema(conn)

        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='claims'"
        ).fetchall()
        assert len(rows) == 1

    def test_v1_to_v2_migration_preserves_existing_data(self) -> None:
        conn = _in_memory_conn()
        conn.executescript(SCHEMA_DDL_V1)
        conn.execute("INSERT OR REPLACE INTO schema_meta(key, value) VALUES ('version', '1')")
        conn.execute(
            """
            INSERT INTO research_runs (
                run_id, topic, platform, started_at,
                export_paths_json, warning_count, exit_status,
                config_snapshot_json, schema_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("existing-run", "test", "youtube", "2024-01-01", "{}", 0, "ok", "{}", 1),
        )
        conn.commit()

        ensure_schema(conn)

        row = conn.execute(
            "SELECT run_id FROM research_runs WHERE run_id='existing-run'"
        ).fetchone()
        assert row is not None


class TestInsertClaims:
    def _setup(self) -> tuple[sqlite3.Connection, int, int, int]:
        conn = _full_schema_conn()
        with conn:
            run_pk = _insert_run(conn)
            source_pk = _insert_source(conn)
            snap_pk = _insert_snapshot(conn, source_pk, run_pk)
        return conn, run_pk, source_pk, snap_pk

    def test_insert_valid_claim_returns_count(self) -> None:
        conn, run_pk, source_pk, snap_pk = self._setup()
        count = insert_claims(
            conn,
            run_pk,
            snap_pk,
            source_pk,
            [_sample_claim()],
            source_url="https://youtube.com/watch?v=vid1",
            source_title="Test Video",
            created_at="2024-01-01T00:00:00",
        )
        assert count == 1

    def test_insert_multiple_claims_returns_count(self) -> None:
        conn, run_pk, source_pk, snap_pk = self._setup()
        claims = [_sample_claim("id1"), _sample_claim("id2"), _sample_claim("id3")]
        count = insert_claims(
            conn,
            run_pk,
            snap_pk,
            source_pk,
            claims,
            source_url="u",
            source_title="t",
            created_at="2024-01-01",
        )
        assert count == 3

    def test_insert_skips_non_dict_claims(self) -> None:
        conn, run_pk, source_pk, snap_pk = self._setup()
        count = insert_claims(
            conn,
            run_pk,
            snap_pk,
            source_pk,
            ["not-a-dict", 42, None],
            source_url="u",
            source_title="t",
            created_at="2024-01-01",
        )
        assert count == 0

    def test_insert_skips_claims_missing_claim_id(self) -> None:
        conn, run_pk, source_pk, snap_pk = self._setup()
        claim = {**_sample_claim(), "claim_id": ""}
        count = insert_claims(
            conn,
            run_pk,
            snap_pk,
            source_pk,
            [claim],
            source_url="u",
            source_title="t",
            created_at="2024-01-01",
        )
        assert count == 0

    def test_duplicate_claim_id_per_snapshot_ignored(self) -> None:
        conn, run_pk, source_pk, snap_pk = self._setup()
        claim = _sample_claim()
        insert_claims(
            conn,
            run_pk,
            snap_pk,
            source_pk,
            [claim],
            source_url="u",
            source_title="t",
            created_at="2024-01-01",
        )
        count2 = insert_claims(
            conn,
            run_pk,
            snap_pk,
            source_pk,
            [claim],
            source_url="u",
            source_title="t",
            created_at="2024-01-01",
        )
        assert count2 == 1
        rows = conn.execute("SELECT COUNT(*) FROM claims").fetchone()
        assert rows[0] == 1

    def test_entities_json_stored_as_valid_json(self) -> None:
        conn, run_pk, source_pk, snap_pk = self._setup()
        claim = {**_sample_claim(), "entities": ["AI", "OpenAI", "50%"]}
        insert_claims(
            conn,
            run_pk,
            snap_pk,
            source_pk,
            [claim],
            source_url="u",
            source_title="t",
            created_at="2024-01-01",
        )
        row = conn.execute("SELECT entities_json FROM claims").fetchone()
        parsed = json.loads(row[0])
        assert parsed == ["AI", "OpenAI", "50%"]

    def test_booleans_stored_as_integers(self) -> None:
        conn, run_pk, source_pk, snap_pk = self._setup()
        claim = {**_sample_claim(), "needs_corroboration": True, "needs_review": False}
        insert_claims(
            conn,
            run_pk,
            snap_pk,
            source_pk,
            [claim],
            source_url="u",
            source_title="t",
            created_at="2024-01-01",
        )
        row = conn.execute("SELECT needs_corroboration, needs_review FROM claims").fetchone()
        assert row[0] == 1
        assert row[1] == 0


class TestSQLitePersistTechClaims:
    def _make_data(self, extracted_claims: list | None = None) -> dict:
        item: dict = {
            "id": "vid1",
            "url": "https://youtube.com/watch?v=vid1",
            "title": "Test Video",
            "text_surrogate": {
                "platform": "youtube",
                "source_id": "vid1",
                "primary_text": "some text",
                "primary_text_source": "transcript",
                "evidence_tier": "transcript_rich",
            },
        }
        if extracted_claims is not None:
            item["extracted_claims"] = extracted_claims
        return item

    def _run_persist(self, item: dict, tmp_path) -> dict:
        import asyncio

        from social_research_probe.technologies.persistence.sqlite import SQLitePersistTech

        db_path = tmp_path / "test.db"
        data = {
            "report": {
                "topic": "ai",
                "platform": "youtube",
                "items_top_n": [item],
            },
            "db_path": str(db_path),
            "config": {},
            "persist_transcript_text": False,
            "persist_comment_text": False,
        }
        return asyncio.run(SQLitePersistTech()._execute(data))

    def test_persist_tech_writes_claims_when_present(self, tmp_path) -> None:
        item = self._make_data(extracted_claims=[_sample_claim()])
        self._run_persist(item, tmp_path)

        conn = sqlite3.connect(str(tmp_path / "test.db"))
        row = conn.execute("SELECT COUNT(*) FROM claims").fetchone()
        conn.close()
        assert row[0] == 1

    def test_persist_tech_handles_item_without_claims(self, tmp_path) -> None:
        item = self._make_data(extracted_claims=None)
        result = self._run_persist(item, tmp_path)
        assert result["persisted_source_count"] == 1

        conn = sqlite3.connect(str(tmp_path / "test.db"))
        row = conn.execute("SELECT COUNT(*) FROM claims").fetchone()
        conn.close()
        assert row[0] == 0
