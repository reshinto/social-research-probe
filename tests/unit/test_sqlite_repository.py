"""Tests for SQLite repository helpers."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

from social_research_probe.technologies.persistence.sqlite.connection import (
    open_connection,
)
from social_research_probe.technologies.persistence.sqlite.repository import (
    derive_run_id,
    derive_source_key,
    dumps,
    insert_artifacts,
    insert_comments,
    insert_run,
    insert_snapshot,
    insert_text_surrogate,
    insert_transcript,
    insert_warnings,
    sha256_hex,
    upsert_source,
)
from social_research_probe.technologies.persistence.sqlite.schema import ensure_schema


def _db(tmp_path) -> sqlite3.Connection:
    conn = open_connection(tmp_path / "test.db")
    ensure_schema(conn)
    return conn


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _insert_run(conn: sqlite3.Connection, *, run_id: str = "run-1") -> int:
    return insert_run(
        conn,
        run_id=run_id,
        topic="test topic",
        platform="youtube",
        purpose_set=[],
        started_at=_now(),
        finished_at=None,
        html_report_path=None,
        output_dir=None,
        export_paths={},
        warning_count=0,
        exit_status="ok",
        config_snapshot={},
        schema_version=1,
    )


def _insert_source(conn: sqlite3.Connection, *, external_id: str = "vid1") -> int:
    return upsert_source(
        conn,
        platform="youtube",
        external_id=external_id,
        url=f"https://youtube.com/watch?v={external_id}",
        title="Test Video",
        description=None,
        channel="Test Channel",
        source_class=None,
        published_at=None,
        now=_now(),
    )


def _insert_snap(conn: sqlite3.Connection, source_pk: int, run_pk: int) -> int:
    return insert_snapshot(
        conn,
        source_pk=source_pk,
        run_pk=run_pk,
        item={"transcript_status": "available"},
        observed_at=_now(),
    )


# --- dumps ---


def test_dumps_deterministic():
    assert dumps({"b": 1, "a": 2}) == '{"a":2,"b":1}'


def test_dumps_rounds_floats():
    assert dumps({"x": 1.1234567}) == '{"x":1.123457}'


def test_dumps_handles_list():
    assert dumps([3, 1, 2]) == "[3,1,2]"


def test_dumps_handles_tuple():
    assert dumps((1, 2)) == "[1,2]"


def test_dumps_nested():
    assert dumps({"a": {"c": 3, "b": 2}}) == '{"a":{"b":2,"c":3}}'


# --- sha256_hex ---


def test_sha256_hex_none_passthrough():
    assert sha256_hex(None) is None


def test_sha256_hex_returns_hex_string():
    result = sha256_hex("hello")
    assert isinstance(result, str)
    assert len(result) == 64


def test_sha256_hex_deterministic():
    assert sha256_hex("abc") == sha256_hex("abc")


# --- derive_source_key ---


def test_derive_source_key_from_text_surrogate():
    item = {"text_surrogate": {"platform": "youtube", "source_id": "abc123"}}
    assert derive_source_key(item) == ("youtube", "abc123")


def test_derive_source_key_from_item_id():
    item = {"id": "xyz", "text_surrogate": {}}
    assert derive_source_key(item) == ("youtube", "xyz")


def test_derive_source_key_fallback_url_hash():
    item = {"url": "https://example.com/video"}
    platform, external_id = derive_source_key(item)
    assert platform == "youtube"
    assert external_id.startswith("url-")
    assert len(external_id) == 4 + 16  # "url-" + 16 hex chars


def test_derive_source_key_fallback_url_hash_stable():
    item = {"url": "https://example.com/video"}
    assert derive_source_key(item) == derive_source_key(item)


def test_derive_source_key_empty_item():
    platform, external_id = derive_source_key({})
    assert platform == "youtube"
    assert external_id.startswith("url-")


# --- derive_run_id ---


def test_derive_run_id_from_plain_path():
    report = {"html_report_path": "/tmp/reports/my-report-20240101.html"}
    assert derive_run_id(report) == "my-report-20240101"


def test_derive_run_id_from_file_uri():
    report = {"html_report_path": "file:///tmp/reports/my-report-20240101.html"}
    assert derive_run_id(report) == "my-report-20240101"


def test_derive_run_id_fallback_uuid():
    run_id = derive_run_id({})
    assert isinstance(run_id, str)
    assert len(run_id) == 32  # uuid4().hex


def test_derive_run_id_fallback_uuid_unique():
    assert derive_run_id({}) != derive_run_id({})


def test_derive_run_id_filters_serve_command():
    report = {"report_path": "srp serve /tmp/something"}
    run_id = derive_run_id(report)
    assert isinstance(run_id, str)
    assert len(run_id) == 32


# --- insert_run ---


def test_insert_run_returns_pk(tmp_path):
    conn = _db(tmp_path)
    pk = _insert_run(conn)
    assert isinstance(pk, int)
    assert pk >= 1
    conn.close()


def test_insert_run_purpose_set_json(tmp_path):
    conn = _db(tmp_path)
    pk = insert_run(
        conn,
        run_id="run-x",
        topic="t",
        platform="youtube",
        purpose_set=["academic", "policy"],
        started_at=_now(),
        finished_at=None,
        html_report_path=None,
        output_dir=None,
        export_paths={"sources_csv": "/tmp/s.csv"},
        warning_count=2,
        exit_status="partial",
        config_snapshot={"max_items": 10},
        schema_version=1,
    )
    row = conn.execute(
        "SELECT purpose_set_json, export_paths_json, warning_count, exit_status FROM research_runs WHERE id=?",
        (pk,),
    ).fetchone()
    assert row[0] == '["academic","policy"]'
    assert row[1] == '{"sources_csv":"/tmp/s.csv"}'
    assert row[2] == 2
    assert row[3] == "partial"
    conn.close()


# --- upsert_source ---


def test_upsert_source_inserts(tmp_path):
    conn = _db(tmp_path)
    pk = _insert_source(conn)
    assert isinstance(pk, int)
    conn.close()


def test_upsert_source_sets_first_seen(tmp_path):
    conn = _db(tmp_path)
    now = _now()
    pk = upsert_source(
        conn,
        platform="youtube",
        external_id="v1",
        url="https://yt.com/v1",
        title="T1",
        description="Desc",
        channel="Chan",
        source_class="primary",
        published_at="2024-01-01",
        now=now,
    )
    row = conn.execute("SELECT first_seen_at FROM sources WHERE id=?", (pk,)).fetchone()
    assert row[0] == now
    conn.close()


def test_upsert_source_updates_last_seen(tmp_path):
    conn = _db(tmp_path)
    t1 = "2024-01-01T00:00:00+00:00"
    t2 = "2024-06-01T00:00:00+00:00"
    upsert_source(
        conn,
        platform="youtube",
        external_id="v1",
        url="https://yt.com/v1",
        title="Old Title",
        description=None,
        channel=None,
        source_class=None,
        published_at=None,
        now=t1,
    )
    pk2 = upsert_source(
        conn,
        platform="youtube",
        external_id="v1",
        url="https://yt.com/v1",
        title="New Title",
        description=None,
        channel=None,
        source_class=None,
        published_at=None,
        now=t2,
    )
    row = conn.execute(
        "SELECT first_seen_at, last_seen_at, title FROM sources WHERE id=?", (pk2,)
    ).fetchone()
    assert row[0] == t1
    assert row[1] == t2
    assert row[2] == "New Title"
    conn.close()


# --- insert_snapshot ---


def test_insert_snapshot_returns_pk(tmp_path):
    conn = _db(tmp_path)
    run_pk = _insert_run(conn)
    src_pk = _insert_source(conn)
    snap_pk = _insert_snap(conn, src_pk, run_pk)
    assert isinstance(snap_pk, int)
    conn.close()


def test_insert_snapshot_stores_scores_and_features(tmp_path):
    conn = _db(tmp_path)
    run_pk = _insert_run(conn)
    src_pk = _insert_source(conn)
    item = {
        "scores": {"trust": 0.8, "trend": 0.5},
        "features": {"recency_days": 30},
        "transcript_status": "available",
        "evidence_tier": "transcript",
    }
    snap_pk = insert_snapshot(conn, source_pk=src_pk, run_pk=run_pk, item=item, observed_at=_now())
    row = conn.execute(
        "SELECT scores_json, features_json, evidence_tier FROM source_snapshots WHERE id=?",
        (snap_pk,),
    ).fetchone()
    assert row[0] == '{"trend":0.5,"trust":0.8}'
    assert row[1] == '{"recency_days":30}'
    assert row[2] == "transcript"
    conn.close()


# --- insert_comments ---


def test_insert_comments_persist_text_true(tmp_path):
    conn = _db(tmp_path)
    run_pk = _insert_run(conn)
    src_pk = _insert_source(conn)
    snap_pk = _insert_snap(conn, src_pk, run_pk)
    comments = [{"comment_id": "c1", "author": "Alice", "text": "Hello"}]
    insert_comments(conn, snap_pk, comments, persist_text=True)
    row = conn.execute("SELECT text, text_digest FROM comments WHERE comment_id='c1'").fetchone()
    assert row[0] == "Hello"
    assert row[1] == sha256_hex("Hello")
    conn.close()


def test_insert_comments_persist_text_false_nulls_text(tmp_path):
    conn = _db(tmp_path)
    run_pk = _insert_run(conn)
    src_pk = _insert_source(conn)
    snap_pk = _insert_snap(conn, src_pk, run_pk)
    comments = [{"comment_id": "c1", "text": "Hello"}]
    insert_comments(conn, snap_pk, comments, persist_text=False)
    row = conn.execute("SELECT text, text_digest FROM comments WHERE comment_id='c1'").fetchone()
    assert row[0] is None
    assert row[1] == sha256_hex("Hello")
    conn.close()


def test_insert_comments_deduplicates(tmp_path):
    conn = _db(tmp_path)
    run_pk = _insert_run(conn)
    src_pk = _insert_source(conn)
    snap_pk = _insert_snap(conn, src_pk, run_pk)
    comments = [{"comment_id": "c1", "text": "A"}, {"comment_id": "c1", "text": "B"}]
    insert_comments(conn, snap_pk, comments, persist_text=True)
    count = conn.execute("SELECT COUNT(*) FROM comments WHERE comment_id='c1'").fetchone()[0]
    assert count == 1
    conn.close()


def test_insert_comments_skips_missing_comment_id(tmp_path):
    conn = _db(tmp_path)
    run_pk = _insert_run(conn)
    src_pk = _insert_source(conn)
    snap_pk = _insert_snap(conn, src_pk, run_pk)
    insert_comments(conn, snap_pk, [{"author": "Alice"}], persist_text=True)
    count = conn.execute("SELECT COUNT(*) FROM comments").fetchone()[0]
    assert count == 0
    conn.close()


def test_insert_comments_skips_non_dict(tmp_path):
    conn = _db(tmp_path)
    run_pk = _insert_run(conn)
    src_pk = _insert_source(conn)
    snap_pk = _insert_snap(conn, src_pk, run_pk)
    insert_comments(conn, snap_pk, ["not a dict", 42], persist_text=True)  # type: ignore[list-item]
    count = conn.execute("SELECT COUNT(*) FROM comments").fetchone()[0]
    assert count == 0
    conn.close()


# --- insert_transcript ---


def test_insert_transcript_persist_text_true(tmp_path):
    conn = _db(tmp_path)
    run_pk = _insert_run(conn)
    src_pk = _insert_source(conn)
    snap_pk = _insert_snap(conn, src_pk, run_pk)
    item = {"transcript": "Hello world", "transcript_status": "available"}
    insert_transcript(conn, snap_pk, item, persist_text=True)
    row = conn.execute(
        "SELECT text, text_digest, char_count, status FROM transcripts WHERE source_snapshot_id=?",
        (snap_pk,),
    ).fetchone()
    assert row[0] == "Hello world"
    assert row[1] == sha256_hex("Hello world")
    assert row[2] == 11
    assert row[3] == "available"
    conn.close()


def test_insert_transcript_persist_text_false_nulls_text(tmp_path):
    conn = _db(tmp_path)
    run_pk = _insert_run(conn)
    src_pk = _insert_source(conn)
    snap_pk = _insert_snap(conn, src_pk, run_pk)
    item = {"transcript": "Hello world", "transcript_status": "available"}
    insert_transcript(conn, snap_pk, item, persist_text=False)
    row = conn.execute(
        "SELECT text, text_digest, char_count FROM transcripts WHERE source_snapshot_id=?",
        (snap_pk,),
    ).fetchone()
    assert row[0] is None
    assert row[1] == sha256_hex("Hello world")
    assert row[2] == 11
    conn.close()


def test_insert_transcript_unavailable_status(tmp_path):
    conn = _db(tmp_path)
    run_pk = _insert_run(conn)
    src_pk = _insert_source(conn)
    snap_pk = _insert_snap(conn, src_pk, run_pk)
    insert_transcript(conn, snap_pk, {"transcript_status": "unavailable"}, persist_text=False)
    row = conn.execute(
        "SELECT status, text, char_count FROM transcripts WHERE source_snapshot_id=?",
        (snap_pk,),
    ).fetchone()
    assert row[0] == "unavailable"
    assert row[1] is None
    assert row[2] is None
    conn.close()


# --- insert_text_surrogate ---


def test_insert_text_surrogate_stores_all_fields(tmp_path):
    conn = _db(tmp_path)
    run_pk = _insert_run(conn)
    src_pk = _insert_source(conn)
    snap_pk = _insert_snap(conn, src_pk, run_pk)
    surrogate = {
        "primary_text": "Main content here",
        "primary_text_source": "transcript",
        "evidence_layers": ["transcript", "description"],
        "evidence_tier": "transcript",
        "char_count": 17,
        "confidence_penalties": ["no_comments"],
        "warnings": ["transcript short"],
    }
    insert_text_surrogate(conn, snap_pk, surrogate)
    row = conn.execute(
        """SELECT primary_text, primary_text_source, text_digest, evidence_layers_json,
                  evidence_tier, char_count, confidence_penalties_json, warnings_json
           FROM text_surrogates WHERE source_snapshot_id=?""",
        (snap_pk,),
    ).fetchone()
    assert row[0] == "Main content here"
    assert row[1] == "transcript"
    assert row[2] == sha256_hex("Main content here")
    assert row[3] == '["transcript","description"]'
    assert row[4] == "transcript"
    assert row[5] == 17
    assert row[6] == '["no_comments"]'
    assert row[7] == '["transcript short"]'
    conn.close()


# --- insert_warnings ---


def test_insert_warnings_string(tmp_path):
    conn = _db(tmp_path)
    run_pk = _insert_run(conn)
    n = insert_warnings(conn, run_pk, ["warn1", "warn2"])
    assert n == 2
    rows = conn.execute("SELECT message, kind FROM warnings WHERE run_id=?", (run_pk,)).fetchall()
    assert {r[0] for r in rows} == {"warn1", "warn2"}
    assert all(r[1] is None for r in rows)
    conn.close()


def test_insert_warnings_dict(tmp_path):
    conn = _db(tmp_path)
    run_pk = _insert_run(conn)
    insert_warnings(conn, run_pk, [{"message": "oops", "kind": "api_error"}])
    row = conn.execute("SELECT message, kind FROM warnings WHERE run_id=?", (run_pk,)).fetchone()
    assert row[0] == "oops"
    assert row[1] == "api_error"
    conn.close()


# --- insert_artifacts ---


def test_insert_artifacts_html_and_export_paths(tmp_path):
    conn = _db(tmp_path)
    run_pk = _insert_run(conn)
    n = insert_artifacts(
        conn,
        run_pk,
        html_report_path="/tmp/report.html",
        export_paths={"sources_csv": "/tmp/s.csv", "comments_csv": "/tmp/c.csv"},
        created_at=_now(),
    )
    assert n == 3
    rows = conn.execute(
        "SELECT kind, path FROM artifacts WHERE run_id=? ORDER BY kind", (run_pk,)
    ).fetchall()
    kinds = {r[0] for r in rows}
    assert kinds == {"html_report", "sources_csv", "comments_csv"}
    conn.close()


def test_insert_artifacts_no_html(tmp_path):
    conn = _db(tmp_path)
    run_pk = _insert_run(conn)
    n = insert_artifacts(conn, run_pk, html_report_path=None, export_paths={}, created_at=_now())
    assert n == 0
    conn.close()
