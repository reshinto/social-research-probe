"""Tests for insert_narratives repository function."""

from __future__ import annotations

import sqlite3

from social_research_probe.technologies.persistence.sqlite.repository import (
    insert_narratives,
)
from social_research_probe.technologies.persistence.sqlite.schema import ensure_schema


def _setup_db() -> tuple[sqlite3.Connection, int]:
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON")
    ensure_schema(conn)
    conn.execute(
        "INSERT INTO research_runs (run_id, topic, platform, started_at, schema_version) "
        "VALUES ('r1', 'test', 'youtube', '2024-01-01', 4)"
    )
    conn.commit()
    run_pk = conn.execute("SELECT id FROM research_runs WHERE run_id = 'r1'").fetchone()[0]
    return conn, run_pk


def _cluster(
    narrative_id: str = "n1",
    cluster_type: str = "theme",
    claim_ids: list[str] | None = None,
    source_ids: list[str] | None = None,
    source_urls: list[str] | None = None,
) -> dict:
    return {
        "narrative_id": narrative_id,
        "title": f"{cluster_type}: AI",
        "summary": "AI is transformative; ML grows",
        "cluster_type": cluster_type,
        "entities": ["AI", "ML"],
        "keywords": ["artificial intelligence"],
        "evidence_tiers": ["transcript_rich"],
        "corroboration_statuses": ["supported"],
        "representative_claims": ["AI is transformative"],
        "claim_ids": claim_ids or ["c1", "c2"],
        "source_ids": source_ids or ["s1"],
        "source_urls": source_urls or ["https://example.com/v1"],
        "source_count": 1,
        "claim_count": 2,
        "confidence": 0.75,
        "opportunity_score": 0.4,
        "risk_score": 0.1,
        "contradiction_count": 0,
        "needs_review_count": 0,
        "created_at": "2024-01-01T00:00:00",
    }


class TestInsertNarratives:
    def test_returns_count(self) -> None:
        conn, run_pk = _setup_db()
        count = insert_narratives(
            conn, run_pk, [_cluster("n1"), _cluster("n2")], created_at="2024-01-01"
        )
        assert count == 2
        conn.close()

    def test_empty_clusters_noop(self) -> None:
        conn, run_pk = _setup_db()
        count = insert_narratives(conn, run_pk, [], created_at="2024-01-01")
        assert count == 0
        conn.close()

    def test_non_dict_skipped(self) -> None:
        conn, run_pk = _setup_db()
        count = insert_narratives(
            conn, run_pk, [_cluster(), "invalid", None], created_at="2024-01-01"
        )
        assert count == 1
        conn.close()

    def test_missing_narrative_id_skipped(self) -> None:
        conn, run_pk = _setup_db()
        bad = _cluster()
        bad["narrative_id"] = ""
        count = insert_narratives(conn, run_pk, [bad], created_at="2024-01-01")
        assert count == 0
        conn.close()

    def test_cluster_fields_persisted(self) -> None:
        conn, run_pk = _setup_db()
        insert_narratives(conn, run_pk, [_cluster()], created_at="2024-01-01")
        row = conn.execute(
            "SELECT narrative_id, title, cluster_type, confidence, opportunity_score, risk_score "
            "FROM narrative_clusters WHERE run_id = ?",
            (run_pk,),
        ).fetchone()
        assert row[0] == "n1"
        assert row[1] == "theme: AI"
        assert row[2] == "theme"
        assert abs(row[3] - 0.75) < 0.001
        assert abs(row[4] - 0.4) < 0.001
        assert abs(row[5] - 0.1) < 0.001
        conn.close()

    def test_junction_claims_populated(self) -> None:
        conn, run_pk = _setup_db()
        insert_narratives(
            conn, run_pk, [_cluster(claim_ids=["c1", "c2", "c3"])], created_at="2024-01-01"
        )
        rows = conn.execute("SELECT claim_id FROM narrative_claims ORDER BY claim_id").fetchall()
        assert [r[0] for r in rows] == ["c1", "c2", "c3"]
        conn.close()

    def test_junction_sources_populated(self) -> None:
        conn, run_pk = _setup_db()
        insert_narratives(
            conn,
            run_pk,
            [_cluster(source_ids=["s1", "s2"], source_urls=["http://a", "http://b"])],
            created_at="2024-01-01",
        )
        rows = conn.execute(
            "SELECT source_id, source_url FROM narrative_sources ORDER BY source_id"
        ).fetchall()
        assert rows == [("s1", "http://a"), ("s2", "http://b")]
        conn.close()

    def test_unique_constraint_enforced(self) -> None:
        conn, run_pk = _setup_db()
        insert_narratives(conn, run_pk, [_cluster("n1")], created_at="2024-01-01")
        count = insert_narratives(conn, run_pk, [_cluster("n1")], created_at="2024-01-01")
        assert count == 1
        total = conn.execute(
            "SELECT COUNT(*) FROM narrative_clusters WHERE run_id = ?", (run_pk,)
        ).fetchone()[0]
        assert total == 1
        conn.close()

    def test_cascade_delete(self) -> None:
        conn, run_pk = _setup_db()
        insert_narratives(conn, run_pk, [_cluster()], created_at="2024-01-01")
        narr_pk = conn.execute("SELECT id FROM narrative_clusters").fetchone()[0]
        conn.execute("DELETE FROM narrative_clusters WHERE id = ?", (narr_pk,))
        assert conn.execute("SELECT COUNT(*) FROM narrative_claims").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM narrative_sources").fetchone()[0] == 0
        conn.close()
