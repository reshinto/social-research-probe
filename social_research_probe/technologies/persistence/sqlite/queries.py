"""Read-only query functions for claims, reviews, and notes."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime


def _rows_to_dicts(cursor: sqlite3.Cursor) -> list[dict]:
    """Build tabular rows for CSV or HTML output.

    Keeping export text here prevents renderers from duplicating wording and column order.

    Args:
        cursor: SQLite cursor whose current row or description is being inspected.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            _rows_to_dicts(
                cursor="AI safety",
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
    """
    cols = [desc[0] for desc in cursor.description]
    return [dict(zip(cols, row, strict=True)) for row in cursor.fetchall()]


def _row_to_dict(cursor: sqlite3.Cursor) -> dict | None:
    """Convert one SQLite row into a plain dictionary.

    Persistence helpers keep SQL and schema details at the storage boundary instead of leaking them
    through pipeline code.

    Args:
        cursor: SQLite cursor whose current row or description is being inspected.

    Returns:
        Dictionary with stable keys consumed by downstream project code.

    Examples:
        Input:
            _row_to_dict(
                cursor="AI safety",
            )
        Output:
            {"enabled": True}
    """
    row = cursor.fetchone()
    if row is None:
        return None
    cols = [desc[0] for desc in cursor.description]
    return dict(zip(cols, row, strict=True))


def resolve_claim_pk(conn: sqlite3.Connection, claim_id: str) -> int | None:
    """Look up claims.id from claim_id TEXT. Returns None if not found.

    Persistence helpers keep database schema decisions at the storage boundary instead of spreading

    SQL-shaped data through the pipeline.

    Args:
        conn: Open SQLite connection for the current transaction.
        claim_id: Database id of the claim being queried, reviewed, or annotated.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            resolve_claim_pk(
                conn=sqlite3.Connection(":memory:"),
                claim_id={"text": "The model reduces latency by 30%."},
            )
        Output:
            "AI safety"
    """
    row = conn.execute("SELECT id FROM claims WHERE claim_id = ?", (claim_id,)).fetchone()
    return row[0] if row else None


def query_claims(
    conn: sqlite3.Connection,
    *,
    run_id: int | None = None,
    topic: str | None = None,
    claim_type: str | None = None,
    needs_review: bool = False,
    needs_corroboration: bool = False,
    corroboration_status: str | None = None,
    extraction_method: str | None = None,
    limit: int = 100,
) -> list[dict]:
    """SELECT claims with optional filters. JOINs research_runs for topic, LEFT JOINs claim_reviews.

    Persistence helpers keep database schema decisions at the storage boundary instead of spreading

    SQL-shaped data through the pipeline.

    Args:
        conn: Open SQLite connection for the current transaction.
        run_id: Stable identifier for one research run.
        topic: Research topic text or existing topic list used for classification and suggestions.
        claim_type: Claim text or claim dictionary being extracted, classified, reviewed, or
                    corroborated.
        needs_review: Flag that selects the branch for this operation.
        needs_corroboration: Flag that selects the branch for this operation.
                corroboration_status: Stored corroboration status used to filter claim rows.
        extraction_method: Extraction method value that changes the behavior described by this
                           helper.
        limit: Count, database id, index, or limit that bounds the work being performed.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            query_claims(
                conn=sqlite3.Connection(":memory:"),
                run_id="AI safety",
                topic="AI safety",
                claim_type={"text": "The model reduces latency by 30%."},
                needs_review=True,
                needs_corroboration=True,
                corroboration_status="AI safety",
                extraction_method="AI safety",
                limit=3,
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
    """
    parts = [
        "SELECT c.*, rr.topic, cr.review_status, cr.importance",
        "FROM claims c",
        "JOIN research_runs rr ON c.run_id = rr.id",
        "LEFT JOIN claim_reviews cr ON cr.claim_pk = c.id",
        "WHERE 1=1",
    ]
    params: list[object] = []

    if run_id is not None:
        parts.append("AND c.run_id = ?")
        params.append(run_id)
    if topic is not None:
        parts.append("AND rr.topic = ?")
        params.append(topic)
    if claim_type is not None:
        parts.append("AND c.claim_type = ?")
        params.append(claim_type)
    if needs_review:
        parts.append("AND c.needs_review = 1")
    if needs_corroboration:
        parts.append("AND c.needs_corroboration = 1")
    if corroboration_status is not None:
        parts.append("AND c.corroboration_status = ?")
        params.append(corroboration_status)
    if extraction_method is not None:
        parts.append("AND c.extraction_method = ?")
        params.append(extraction_method)

    parts.append("ORDER BY c.id DESC LIMIT ?")
    params.append(limit)

    sql = " ".join(parts)
    cur = conn.execute(sql, params)
    return _rows_to_dicts(cur)


def get_claim(conn: sqlite3.Connection, claim_id: str) -> dict | None:
    """Single claim with source info and review status.

    Persistence helpers keep database schema decisions at the storage boundary instead of spreading

    SQL-shaped data through the pipeline.

    Args:
        conn: Open SQLite connection for the current transaction.
        claim_id: Database id of the claim being queried, reviewed, or annotated.

    Returns:
        Dictionary with stable keys consumed by downstream project code.

    Examples:
        Input:
            get_claim(
                conn=sqlite3.Connection(":memory:"),
                claim_id={"text": "The model reduces latency by 30%."},
            )
        Output:
            {"enabled": True}
    """
    sql = """
        SELECT c.*, rr.topic, cr.review_status, cr.importance, cr.review_note, cr.quality_score
        FROM claims c
        JOIN research_runs rr ON c.run_id = rr.id
        LEFT JOIN claim_reviews cr ON cr.claim_pk = c.id
        WHERE c.claim_id = ?
    """
    cur = conn.execute(sql, (claim_id,))
    return _row_to_dict(cur)


def claim_stats(conn: sqlite3.Connection) -> dict:
    """Aggregated claim statistics.

    Persistence helpers keep database schema decisions at the storage boundary instead of spreading

    SQL-shaped data through the pipeline.

    Args:
        conn: Open SQLite connection for the current transaction.

    Returns:
        Dictionary with stable keys consumed by downstream project code.

    Examples:
        Input:
            claim_stats(
                conn=sqlite3.Connection(":memory:"),
            )
        Output:
            {"enabled": True}
    """
    total = conn.execute("SELECT COUNT(*) FROM claims").fetchone()[0]
    if total == 0:
        return {
            "total": 0,
            "by_type": {},
            "by_method": {},
            "needs_review": 0,
            "needs_corroboration": 0,
            "by_review_status": {},
        }

    by_type: dict[str, int] = {}
    for row in conn.execute(
        "SELECT claim_type, COUNT(*) FROM claims GROUP BY claim_type"
    ).fetchall():
        by_type[row[0] or "unknown"] = row[1]

    by_method: dict[str, int] = {}
    for row in conn.execute(
        "SELECT extraction_method, COUNT(*) FROM claims GROUP BY extraction_method"
    ).fetchall():
        by_method[row[0] or "unknown"] = row[1]

    needs_review = conn.execute("SELECT COUNT(*) FROM claims WHERE needs_review = 1").fetchone()[0]

    needs_corroboration = conn.execute(
        "SELECT COUNT(*) FROM claims WHERE needs_corroboration = 1"
    ).fetchone()[0]

    by_review_status: dict[str, int] = {}
    for row in conn.execute(
        "SELECT COALESCE(cr.review_status, 'unreviewed'), COUNT(*) "
        "FROM claims c LEFT JOIN claim_reviews cr ON cr.claim_pk = c.id "
        "GROUP BY COALESCE(cr.review_status, 'unreviewed')"
    ).fetchall():
        by_review_status[row[0]] = row[1]

    return {
        "total": total,
        "by_type": by_type,
        "by_method": by_method,
        "needs_review": needs_review,
        "needs_corroboration": needs_corroboration,
        "by_review_status": by_review_status,
    }


def upsert_claim_review(
    conn: sqlite3.Connection,
    claim_pk: int,
    *,
    claim_id: str,
    run_id: int,
    review_status: str,
    review_note: str = "",
    importance: str | None = None,
    quality_score: float | None = None,
) -> int:
    """INSERT OR REPLACE into claim_reviews. Returns rowid.

    Persistence helpers keep database schema decisions at the storage boundary instead of spreading

    SQL-shaped data through the pipeline.

    Args:
        conn: Open SQLite connection for the current transaction.
        claim_pk: Count, database id, index, or limit that bounds the work being performed.
        claim_id: Database id of the claim being queried, reviewed, or annotated.
        run_id: Count, database id, index, or limit that bounds the work being performed.
        review_status: Human review status selected for the claim.
        review_note: Reviewer note stored with the claim decision.
        importance: Reviewer-provided importance score for the claim.
        quality_score: Reviewer-provided quality score for the claim.

    Returns:
        Integer count, limit, status code, or timeout used by the caller.

    Examples:
        Input:
            upsert_claim_review(
                conn=sqlite3.Connection(":memory:"),
                claim_pk={"text": "The model reduces latency by 30%."},
                claim_id={"text": "The model reduces latency by 30%."},
                run_id=3,
                review_status="AI safety",
                review_note="AI safety",
                importance="AI safety",
                quality_score="AI safety",
            )
        Output:
            5
    """
    reviewed_at = datetime.now(tz=UTC).isoformat()
    cur = conn.execute(
        """
        INSERT OR REPLACE INTO claim_reviews (
            claim_pk, claim_id, run_id, review_status, review_note,
            importance, quality_score, reviewed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            claim_pk,
            claim_id,
            run_id,
            review_status,
            review_note,
            importance,
            quality_score,
            reviewed_at,
        ),
    )
    conn.commit()
    return cur.lastrowid or 0


def insert_claim_note(
    conn: sqlite3.Connection,
    claim_pk: int,
    *,
    claim_id: str,
    run_id: int | None = None,
    note_text: str,
) -> int:
    """Append note. Returns rowid.

    Persistence helpers keep database schema decisions at the storage boundary instead of spreading

    SQL-shaped data through the pipeline.

    Args:
        conn: Open SQLite connection for the current transaction.
        claim_pk: Count, database id, index, or limit that bounds the work being performed.
        claim_id: Database id of the claim being queried, reviewed, or annotated.
        run_id: Stable identifier for one research run.
        note_text: Free-form note text attached to the claim.

    Returns:
        Integer count, limit, status code, or timeout used by the caller.

    Examples:
        Input:
            insert_claim_note(
                conn=sqlite3.Connection(":memory:"),
                claim_pk={"text": "The model reduces latency by 30%."},
                claim_id={"text": "The model reduces latency by 30%."},
                run_id="AI safety",
                note_text="AI safety",
            )
        Output:
            5
    """
    created_at = datetime.now(tz=UTC).isoformat()
    cur = conn.execute(
        """
        INSERT INTO claim_notes (claim_pk, claim_id, run_id, note_text, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (claim_pk, claim_id, run_id, note_text, created_at),
    )
    conn.commit()
    return cur.lastrowid or 0


def get_claim_reviews(conn: sqlite3.Connection, claim_pk: int) -> list[dict]:
    """Get all reviews for a claim.

    Persistence helpers keep database schema decisions at the storage boundary instead of spreading
    SQL-shaped data through the pipeline.

    Args:
        conn: Open SQLite connection for the current transaction.
        claim_pk: Count, database id, index, or limit that bounds the work being performed.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            get_claim_reviews(
                conn=sqlite3.Connection(":memory:"),
                claim_pk={"text": "The model reduces latency by 30%."},
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
    """
    cur = conn.execute(
        "SELECT * FROM claim_reviews WHERE claim_pk = ? ORDER BY reviewed_at DESC",
        (claim_pk,),
    )
    return _rows_to_dicts(cur)


def get_claim_notes(conn: sqlite3.Connection, claim_pk: int) -> list[dict]:
    """Get all notes for a claim, ordered by creation time.

    Persistence helpers keep database schema decisions at the storage boundary instead of spreading
    SQL-shaped data through the pipeline.

    Args:
        conn: Open SQLite connection for the current transaction.
        claim_pk: Count, database id, index, or limit that bounds the work being performed.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            get_claim_notes(
                conn=sqlite3.Connection(":memory:"),
                claim_pk={"text": "The model reduces latency by 30%."},
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
    """
    cur = conn.execute(
        "SELECT * FROM claim_notes WHERE claim_pk = ? ORDER BY created_at ASC",
        (claim_pk,),
    )
    return _rows_to_dicts(cur)
