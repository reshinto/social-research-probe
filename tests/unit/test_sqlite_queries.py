"""Tests for claims query module."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

from social_research_probe.technologies.persistence.sqlite.queries import (
    claim_stats,
    get_claim,
    get_claim_notes,
    get_claim_reviews,
    insert_claim_note,
    query_claims,
    resolve_claim_pk,
    upsert_claim_review,
)
from social_research_probe.technologies.persistence.sqlite.schema import ensure_schema


@contextmanager
def _conn() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys=ON")
    ensure_schema(conn)
    try:
        yield conn
    finally:
        conn.close()


def _seed(conn: sqlite3.Connection) -> dict:
    """Seed DB with a run, source, snapshot, and 3 claims. Returns PKs."""
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

    claims_data = [
        ("c1", "fact_claim", "deterministic", 1, 1, "pending", 10),
        ("c2", "opinion", "llm", 0, 0, "supported", 0),
        ("c3", "prediction", "deterministic", 1, 1, "pending", 5),
    ]
    claim_pks = []
    for cid, ctype, method, nr, nc, cs, pos in claims_data:
        conn.execute(
            "INSERT INTO claims(claim_id, run_id, source_snapshot_id, source_id, "
            "source_url, source_title, claim_text, claim_type, extraction_method, "
            "needs_review, needs_corroboration, corroboration_status, position_in_text, "
            "created_at) "
            "VALUES (?, ?, ?, ?, 'https://y.com/1', 'Video', ?, ?, ?, ?, ?, ?, ?, '2026-01-01')",
            (cid, run_pk, snap_pk, source_pk, f"claim text {cid}", ctype, method, nr, nc, cs, pos),
        )
        claim_pks.append(conn.execute("SELECT last_insert_rowid()").fetchone()[0])

    conn.commit()
    return {"run_pk": run_pk, "source_pk": source_pk, "snap_pk": snap_pk, "claim_pks": claim_pks}


class TestQueryClaims:
    def test_no_filters_returns_all(self):
        with _conn() as conn:
            _seed(conn)
            results = query_claims(conn)
            assert len(results) == 3

    def test_filter_by_run_id(self):
        with _conn() as conn:
            pks = _seed(conn)
            results = query_claims(conn, run_id=pks["run_pk"])
            assert len(results) == 3
            results_empty = query_claims(conn, run_id=9999)
            assert len(results_empty) == 0

    def test_filter_by_topic(self):
        with _conn() as conn:
            _seed(conn)
            results = query_claims(conn, topic="AI safety")
            assert len(results) == 3
            results_empty = query_claims(conn, topic="unknown")
            assert len(results_empty) == 0

    def test_filter_by_claim_type(self):
        with _conn() as conn:
            _seed(conn)
            results = query_claims(conn, claim_type="fact_claim")
            assert len(results) == 1
            assert results[0]["claim_id"] == "c1"

    def test_filter_by_needs_review(self):
        with _conn() as conn:
            _seed(conn)
            results = query_claims(conn, needs_review=True)
            assert len(results) == 2

    def test_filter_by_needs_corroboration(self):
        with _conn() as conn:
            _seed(conn)
            results = query_claims(conn, needs_corroboration=True)
            assert len(results) == 2

    def test_filter_by_corroboration_status(self):
        with _conn() as conn:
            _seed(conn)
            results = query_claims(conn, corroboration_status="supported")
            assert len(results) == 1
            assert results[0]["claim_id"] == "c2"

    def test_filter_by_extraction_method(self):
        with _conn() as conn:
            _seed(conn)
            results = query_claims(conn, extraction_method="llm")
            assert len(results) == 1
            assert results[0]["claim_id"] == "c2"

    def test_limit_enforced(self):
        with _conn() as conn:
            _seed(conn)
            results = query_claims(conn, limit=2)
            assert len(results) == 2

    def test_includes_topic_and_review_status(self):
        with _conn() as conn:
            _seed(conn)
            results = query_claims(conn)
            assert results[0]["topic"] == "AI safety"
            assert results[0]["review_status"] is None


class TestGetClaim:
    def test_found(self):
        with _conn() as conn:
            _seed(conn)
            result = get_claim(conn, "c1")
            assert result is not None
            assert result["claim_id"] == "c1"
            assert result["topic"] == "AI safety"

    def test_not_found(self):
        with _conn() as conn:
            _seed(conn)
            result = get_claim(conn, "nonexistent")
            assert result is None


class TestClaimStats:
    def test_empty_db(self):
        with _conn() as conn:
            stats = claim_stats(conn)
            assert stats["total"] == 0
            assert stats["by_type"] == {}
            assert stats["by_method"] == {}
            assert stats["needs_review"] == 0
            assert stats["needs_corroboration"] == 0
            assert stats["by_review_status"] == {}

    def test_with_data(self):
        with _conn() as conn:
            _seed(conn)
            stats = claim_stats(conn)
            assert stats["total"] == 3
            assert stats["by_type"]["fact_claim"] == 1
            assert stats["by_type"]["opinion"] == 1
            assert stats["by_type"]["prediction"] == 1
            assert stats["by_method"]["deterministic"] == 2
            assert stats["by_method"]["llm"] == 1
            assert stats["needs_review"] == 2
            assert stats["needs_corroboration"] == 2
            assert stats["by_review_status"]["unreviewed"] == 3


class TestUpsertClaimReview:
    def test_insert_and_update(self):
        with _conn() as conn:
            pks = _seed(conn)
            claim_pk = pks["claim_pks"][0]
            run_pk = pks["run_pk"]

            rowid = upsert_claim_review(
                conn, claim_pk, claim_id="c1", run_id=run_pk, review_status="verified"
            )
            assert rowid > 0

            reviews = get_claim_reviews(conn, claim_pk)
            assert len(reviews) == 1
            assert reviews[0]["review_status"] == "verified"

            upsert_claim_review(
                conn,
                claim_pk,
                claim_id="c1",
                run_id=run_pk,
                review_status="rejected",
                review_note="bad claim",
                importance="high",
            )
            reviews = get_claim_reviews(conn, claim_pk)
            assert len(reviews) == 1
            assert reviews[0]["review_status"] == "rejected"
            assert reviews[0]["review_note"] == "bad claim"
            assert reviews[0]["importance"] == "high"


class TestInsertClaimNote:
    def test_appends_multiple(self):
        with _conn() as conn:
            pks = _seed(conn)
            claim_pk = pks["claim_pks"][0]

            insert_claim_note(conn, claim_pk, claim_id="c1", note_text="first note")
            insert_claim_note(conn, claim_pk, claim_id="c1", note_text="second note")

            notes = get_claim_notes(conn, claim_pk)
            assert len(notes) == 2
            assert notes[0]["note_text"] == "first note"
            assert notes[1]["note_text"] == "second note"


class TestResolveClaimPk:
    def test_found(self):
        with _conn() as conn:
            pks = _seed(conn)
            pk = resolve_claim_pk(conn, "c1")
            assert pk == pks["claim_pks"][0]

    def test_not_found(self):
        with _conn() as conn:
            _seed(conn)
            pk = resolve_claim_pk(conn, "nonexistent")
            assert pk is None
