"""Tests for comparison query functions."""

from __future__ import annotations

import json
import sqlite3

from social_research_probe.technologies.persistence.sqlite.comparison_queries import (
    count_for_run,
    get_claims_for_run,
    get_latest_pair,
    get_narratives_for_run,
    get_run,
    get_run_by_text_id,
    get_sources_for_run,
    list_runs,
)
from social_research_probe.technologies.persistence.sqlite.schema import ensure_schema


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys=ON")
    ensure_schema(conn)
    return conn


def _insert_run(conn: sqlite3.Connection, run_id: str, topic: str, started_at: str) -> int:
    """Insert a research run and return its PK."""
    conn.execute(
        "INSERT INTO research_runs (run_id, topic, platform, started_at, schema_version) "
        "VALUES (?, ?, ?, ?, ?)",
        (run_id, topic, "youtube", started_at, 4),
    )
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def _seed_runs(conn: sqlite3.Connection) -> tuple[int, int]:
    """Insert 2 runs and return their PKs."""
    pk_a = _insert_run(conn, "run-aaa", "AI agents", "2024-01-01T00:00:00")
    pk_b = _insert_run(conn, "run-bbb", "AI agents", "2024-01-02T00:00:00")
    return pk_a, pk_b


def _seed_sources(conn: sqlite3.Connection, pk_a: int, pk_b: int) -> None:
    """Insert sources with snapshots across both runs."""
    ts = "2024-01-01T00:00:00"
    conn.execute(
        "INSERT INTO sources (platform, external_id, url, title, first_seen_at, last_seen_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("youtube", "vid1", "https://yt/vid1", "Video 1", ts, ts),
    )
    s1 = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute(
        "INSERT INTO sources (platform, external_id, url, title, first_seen_at, last_seen_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("youtube", "vid2", "https://yt/vid2", "Video 2", ts, ts),
    )
    s2 = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute(
        "INSERT INTO sources (platform, external_id, url, title, first_seen_at, last_seen_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("youtube", "vid3", "https://yt/vid3", "Video 3", ts, ts),
    )
    s3 = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    scores_a = json.dumps({"trust": 0.8, "overall": 0.7})
    scores_b = json.dumps({"trust": 0.9, "overall": 0.75})
    conn.execute(
        "INSERT INTO source_snapshots (source_id, run_id, evidence_tier, scores_json, observed_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (s1, pk_a, "metadata_transcript", scores_a, "2024-01-01T00:00:00"),
    )
    conn.execute(
        "INSERT INTO source_snapshots (source_id, run_id, evidence_tier, scores_json, observed_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (s1, pk_b, "metadata_transcript", scores_b, "2024-01-02T00:00:00"),
    )
    conn.execute(
        "INSERT INTO source_snapshots (source_id, run_id, evidence_tier, scores_json, observed_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (s2, pk_a, "metadata_only", scores_a, "2024-01-01T00:00:00"),
    )
    conn.execute(
        "INSERT INTO source_snapshots (source_id, run_id, evidence_tier, scores_json, observed_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (s3, pk_b, "metadata_transcript", scores_a, "2024-01-02T00:00:00"),
    )


def _seed_claims(conn: sqlite3.Connection, pk_a: int, pk_b: int) -> None:
    """Insert claims for both runs."""
    conn.execute(
        "INSERT INTO claims (claim_id, run_id, claim_text, claim_type, source_url, confidence, "
        "corroboration_status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ("c1", pk_a, "Claim one", "fact_claim", "https://yt/vid1", 0.8, "supported", "2024-01-01"),
    )
    conn.execute(
        "INSERT INTO claims (claim_id, run_id, claim_text, claim_type, source_url, confidence, "
        "corroboration_status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ("c1", pk_b, "Claim one", "fact_claim", "https://yt/vid1", 0.9, "confirmed", "2024-01-02"),
    )
    conn.execute(
        "INSERT INTO claims (claim_id, run_id, claim_text, claim_type, source_url, confidence, "
        "corroboration_status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ("c2", pk_a, "Claim two", "opinion", "https://yt/vid2", 0.6, "pending", "2024-01-01"),
    )


def _seed_narratives(conn: sqlite3.Connection, pk_a: int, pk_b: int) -> None:
    """Insert narratives for both runs."""
    conn.execute(
        "INSERT INTO narrative_clusters (narrative_id, run_id, title, cluster_type, "
        "entities_json, confidence, opportunity_score, risk_score, "
        "source_count, claim_count, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("n1", pk_a, "AI Theme", "theme", '["AI"]', 0.7, 0.3, 0.2, 2, 5, "2024-01-01"),
    )
    conn.execute(
        "INSERT INTO narrative_clusters (narrative_id, run_id, title, cluster_type, "
        "entities_json, confidence, opportunity_score, risk_score, "
        "source_count, claim_count, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("n1", pk_b, "AI Theme", "theme", '["AI"]', 0.8, 0.5, 0.1, 3, 7, "2024-01-02"),
    )


class TestListRuns:
    def test_empty_db(self) -> None:
        conn = _conn()
        assert list_runs(conn) == []
        conn.close()

    def test_returns_ordered_by_started_at_desc(self) -> None:
        conn = _conn()
        _seed_runs(conn)
        runs = list_runs(conn)
        assert len(runs) == 2
        assert runs[0]["run_id"] == "run-bbb"
        assert runs[1]["run_id"] == "run-aaa"
        conn.close()

    def test_filter_by_topic(self) -> None:
        conn = _conn()
        _seed_runs(conn)
        _insert_run(conn, "run-other", "Crypto", "2024-01-03T00:00:00")
        runs = list_runs(conn, topic="AI agents")
        assert len(runs) == 2
        conn.close()

    def test_filter_by_platform(self) -> None:
        conn = _conn()
        _seed_runs(conn)
        runs = list_runs(conn, platform="twitter")
        assert runs == []
        conn.close()

    def test_limit_respected(self) -> None:
        conn = _conn()
        _seed_runs(conn)
        runs = list_runs(conn, limit=1)
        assert len(runs) == 1
        conn.close()


class TestGetRun:
    def test_existing_run(self) -> None:
        conn = _conn()
        pk_a, _ = _seed_runs(conn)
        run = get_run(conn, pk_a)
        assert run is not None
        assert run["run_id"] == "run-aaa"
        conn.close()

    def test_missing_run(self) -> None:
        conn = _conn()
        assert get_run(conn, 999) is None
        conn.close()


class TestGetRunByTextId:
    def test_existing_run(self) -> None:
        conn = _conn()
        _seed_runs(conn)
        run = get_run_by_text_id(conn, "run-bbb")
        assert run is not None
        assert run["topic"] == "AI agents"
        conn.close()

    def test_missing_run(self) -> None:
        conn = _conn()
        assert get_run_by_text_id(conn, "nonexistent") is None
        conn.close()


class TestGetLatestPair:
    def test_returns_pair_ordered_baseline_target(self) -> None:
        conn = _conn()
        _seed_runs(conn)
        pair = get_latest_pair(conn)
        assert pair is not None
        baseline, target = pair
        assert baseline["run_id"] == "run-aaa"
        assert target["run_id"] == "run-bbb"
        conn.close()

    def test_returns_none_if_fewer_than_two(self) -> None:
        conn = _conn()
        _insert_run(conn, "only-one", "topic", "2024-01-01T00:00:00")
        assert get_latest_pair(conn) is None
        conn.close()

    def test_filters_by_topic(self) -> None:
        conn = _conn()
        _seed_runs(conn)
        assert get_latest_pair(conn, topic="Nonexistent") is None
        conn.close()


class TestGetSourcesForRun:
    def test_returns_sources_for_run(self) -> None:
        conn = _conn()
        pk_a, pk_b = _seed_runs(conn)
        _seed_sources(conn, pk_a, pk_b)
        sources_a = get_sources_for_run(conn, pk_a)
        sources_b = get_sources_for_run(conn, pk_b)
        assert len(sources_a) == 2
        assert len(sources_b) == 2
        assert sources_a[0]["external_id"] == "vid1"
        conn.close()

    def test_empty_run(self) -> None:
        conn = _conn()
        pk_a, _ = _seed_runs(conn)
        assert get_sources_for_run(conn, pk_a) == []
        conn.close()


class TestGetClaimsForRun:
    def test_returns_claims_for_specific_run(self) -> None:
        conn = _conn()
        pk_a, pk_b = _seed_runs(conn)
        _seed_claims(conn, pk_a, pk_b)
        claims_a = get_claims_for_run(conn, pk_a)
        claims_b = get_claims_for_run(conn, pk_b)
        assert len(claims_a) == 2
        assert len(claims_b) == 1
        assert claims_a[0]["claim_id"] == "c1"
        conn.close()

    def test_empty_run(self) -> None:
        conn = _conn()
        pk_a, _ = _seed_runs(conn)
        assert get_claims_for_run(conn, pk_a) == []
        conn.close()


class TestGetNarrativesForRun:
    def test_returns_narratives_for_run(self) -> None:
        conn = _conn()
        pk_a, pk_b = _seed_runs(conn)
        _seed_narratives(conn, pk_a, pk_b)
        narr_a = get_narratives_for_run(conn, pk_a)
        narr_b = get_narratives_for_run(conn, pk_b)
        assert len(narr_a) == 1
        assert len(narr_b) == 1
        assert narr_a[0]["narrative_id"] == "n1"
        conn.close()

    def test_empty_run(self) -> None:
        conn = _conn()
        pk_a, _ = _seed_runs(conn)
        assert get_narratives_for_run(conn, pk_a) == []
        conn.close()


class TestCountForRun:
    def test_counts_correct(self) -> None:
        conn = _conn()
        pk_a, pk_b = _seed_runs(conn)
        _seed_sources(conn, pk_a, pk_b)
        _seed_claims(conn, pk_a, pk_b)
        _seed_narratives(conn, pk_a, pk_b)
        counts = count_for_run(conn, pk_a)
        assert counts == {"sources": 2, "claims": 2, "narratives": 1}
        conn.close()

    def test_empty_run(self) -> None:
        conn = _conn()
        pk_a, _ = _seed_runs(conn)
        counts = count_for_run(conn, pk_a)
        assert counts == {"sources": 0, "claims": 0, "narratives": 0}
        conn.close()
