"""Read-only query functions for run comparison."""

from __future__ import annotations

import sqlite3


def _rows_to_dicts(cursor: sqlite3.Cursor) -> list[dict]:
    """Convert all fetched rows to list of plain dicts."""
    cols = [desc[0] for desc in cursor.description]
    return [dict(zip(cols, row, strict=True)) for row in cursor.fetchall()]


def _row_to_dict(cursor: sqlite3.Cursor) -> dict | None:
    """Convert one row to dict or None."""
    row = cursor.fetchone()
    if row is None:
        return None
    cols = [desc[0] for desc in cursor.description]
    return dict(zip(cols, row, strict=True))


def list_runs(
    conn: sqlite3.Connection,
    *,
    topic: str | None = None,
    platform: str | None = None,
    limit: int = 20,
) -> list[dict]:
    """List research runs ordered by started_at DESC."""
    conditions: list[str] = []
    params: list[object] = []
    if topic is not None:
        conditions.append("topic = ?")
        params.append(topic)
    if platform is not None:
        conditions.append("platform = ?")
        params.append(platform)
    where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
    sql = f"SELECT * FROM research_runs{where} ORDER BY started_at DESC LIMIT ?"
    params.append(limit)
    cur = conn.execute(sql, params)
    return _rows_to_dicts(cur)


def get_run(conn: sqlite3.Connection, run_pk: int) -> dict | None:
    """Fetch one run row by integer PK."""
    cur = conn.execute("SELECT * FROM research_runs WHERE id = ?", (run_pk,))
    return _row_to_dict(cur)


def get_run_by_text_id(conn: sqlite3.Connection, run_id: str) -> dict | None:
    """Fetch one run row by TEXT run_id."""
    cur = conn.execute("SELECT * FROM research_runs WHERE run_id = ?", (run_id,))
    return _row_to_dict(cur)


def get_latest_pair(
    conn: sqlite3.Connection,
    *,
    topic: str | None = None,
    platform: str | None = None,
) -> tuple[dict, dict] | None:
    """Return the two most recent runs as (baseline, target) or None if <2 exist."""
    runs = list_runs(conn, topic=topic, platform=platform, limit=2)
    if len(runs) < 2:
        return None
    return (runs[1], runs[0])


def get_previous_matching_run(
    conn: sqlite3.Connection,
    *,
    topic: str,
    platform: str,
    target_run_id: str,
) -> dict | None:
    """Return the most recent matching run before the target run."""
    target = get_run_by_text_id(conn, target_run_id)
    if target is None:
        return None
    cur = conn.execute(
        """
        SELECT *
        FROM research_runs
        WHERE topic = ? AND platform = ? AND run_id != ? AND started_at <= ?
        ORDER BY started_at DESC, id DESC
        LIMIT 1
        """,
        (topic, platform, target_run_id, target.get("started_at") or ""),
    )
    return _row_to_dict(cur)


def get_sources_for_run(conn: sqlite3.Connection, run_pk: int) -> list[dict]:
    """Source + snapshot data for a run."""
    sql = """
        SELECT s.id AS source_id, s.platform, s.external_id, s.url, s.title,
               ss.scores_json, ss.evidence_tier, ss.transcript_status,
               ss.comments_status, ss.corroboration_verdict
        FROM sources s
        JOIN source_snapshots ss ON ss.source_id = s.id
        WHERE ss.run_id = ?
        ORDER BY s.id
    """
    cur = conn.execute(sql, (run_pk,))
    return _rows_to_dicts(cur)


def get_claims_for_run(conn: sqlite3.Connection, run_pk: int) -> list[dict]:
    """All claims rows for a specific run."""
    sql = """
        SELECT claim_id, claim_text, claim_type, source_url, source_title,
               confidence, evidence_tier, corroboration_status,
               contradiction_status, needs_review, extraction_method
        FROM claims
        WHERE run_id = ?
        ORDER BY claim_id
    """
    cur = conn.execute(sql, (run_pk,))
    return _rows_to_dicts(cur)


def get_narratives_for_run(conn: sqlite3.Connection, run_pk: int) -> list[dict]:
    """Narrative clusters for a specific run."""
    sql = """
        SELECT narrative_id, title, cluster_type, entities_json, keywords_json,
               confidence, opportunity_score, risk_score,
               source_count, claim_count, contradiction_count, needs_review_count
        FROM narrative_clusters
        WHERE run_id = ?
        ORDER BY narrative_id
    """
    cur = conn.execute(sql, (run_pk,))
    return _rows_to_dicts(cur)


def count_for_run(conn: sqlite3.Connection, run_pk: int) -> dict[str, int]:
    """Count sources, claims, and narratives for a run."""
    sources = conn.execute(
        "SELECT COUNT(*) FROM source_snapshots WHERE run_id = ?", (run_pk,)
    ).fetchone()[0]
    claims = conn.execute("SELECT COUNT(*) FROM claims WHERE run_id = ?", (run_pk,)).fetchone()[0]
    narratives = conn.execute(
        "SELECT COUNT(*) FROM narrative_clusters WHERE run_id = ?", (run_pk,)
    ).fetchone()[0]
    return {"sources": sources, "claims": claims, "narratives": narratives}


def count_claims_needing_review(conn: sqlite3.Connection, run_pk: int) -> int:
    """Count target-run claims that need review."""
    row = conn.execute(
        "SELECT COUNT(*) FROM claims WHERE run_id = ? AND needs_review = 1", (run_pk,)
    )
    return int(row.fetchone()[0])
