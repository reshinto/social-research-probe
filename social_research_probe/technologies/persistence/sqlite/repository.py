"""Repository helpers for reading and writing srp.db tables."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid


def _normalize(obj: object) -> object:
    if isinstance(obj, float):
        return round(obj, 6)
    if isinstance(obj, dict):
        return {str(k): _normalize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_normalize(v) for v in obj]
    return obj


def dumps(obj: object) -> str:
    return json.dumps(_normalize(obj), sort_keys=True, separators=(",", ":"))


def sha256_hex(text: str | None) -> str | None:
    if text is None:
        return None
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def derive_source_key(item: dict) -> tuple[str, str]:
    surrogate = item.get("text_surrogate") or {}
    platform = surrogate.get("platform") or "youtube"
    external_id = surrogate.get("source_id") or item.get("id") or ""
    if not external_id:
        url = item.get("url") or ""
        external_id = "url-" + hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
    return platform, str(external_id)


def derive_run_id(report: dict) -> str:
    from social_research_probe.utils.pipeline.helpers import resolve_html_report_path

    p = resolve_html_report_path(report)
    if p is not None:
        return p.stem
    return uuid.uuid4().hex


def insert_run(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    topic: str,
    platform: str,
    purpose_set: list,
    started_at: str,
    finished_at: str | None,
    html_report_path: str | None,
    output_dir: str | None,
    export_paths: dict,
    warning_count: int,
    exit_status: str,
    config_snapshot: dict,
    schema_version: int,
) -> int:
    cur = conn.execute(
        """
        INSERT OR IGNORE INTO research_runs (
            run_id, topic, platform, purpose_set_json, started_at, finished_at,
            html_report_path, output_dir, export_paths_json, warning_count,
            exit_status, config_snapshot_json, schema_version
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            topic,
            platform,
            dumps(purpose_set),
            started_at,
            finished_at,
            html_report_path,
            output_dir,
            dumps(export_paths),
            warning_count,
            exit_status,
            dumps(config_snapshot),
            schema_version,
        ),
    )
    if cur.rowcount:
        return cur.lastrowid  # type: ignore[return-value]
    row = conn.execute("SELECT id FROM research_runs WHERE run_id = ?", (run_id,)).fetchone()
    return row[0]


def upsert_source(
    conn: sqlite3.Connection,
    *,
    platform: str,
    external_id: str,
    url: str,
    title: str | None,
    description: str | None,
    channel: str | None,
    source_class: str | None,
    published_at: str | None,
    now: str,
) -> int:
    cur = conn.execute(
        """
        INSERT INTO sources (
            platform, external_id, url, title, description, channel,
            source_class, published_at, first_seen_at, last_seen_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(platform, external_id) DO UPDATE SET
            url          = excluded.url,
            title        = excluded.title,
            description  = excluded.description,
            channel      = excluded.channel,
            source_class = excluded.source_class,
            last_seen_at = excluded.last_seen_at
        RETURNING id
        """,
        (
            platform,
            external_id,
            url,
            title,
            description,
            channel,
            source_class,
            published_at,
            now,
            now,
        ),
    )
    row = cur.fetchone()
    return row[0]


def insert_snapshot(
    conn: sqlite3.Connection,
    *,
    source_pk: int,
    run_pk: int,
    item: dict,
    observed_at: str,
) -> int:
    surrogate: dict = item.get("text_surrogate") or {}
    scores: dict = item.get("scores") or {}
    features: dict = item.get("features") or {}
    raw_metadata: dict[str, object] = {
        k: v
        for k, v in item.items()
        if k
        not in {
            "text_surrogate",
            "scores",
            "features",
            "source_comments",
            "transcript",
            "comments",
        }
    }
    cur = conn.execute(
        """
        INSERT INTO source_snapshots (
            source_id, run_id, summary, one_line_takeaway, evidence_tier,
            transcript_status, comments_status, scores_json, features_json,
            raw_metadata_json, corroboration_verdict, observed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(source_id, run_id) DO UPDATE SET
            summary               = excluded.summary,
            one_line_takeaway     = excluded.one_line_takeaway,
            evidence_tier         = excluded.evidence_tier,
            transcript_status     = excluded.transcript_status,
            comments_status       = excluded.comments_status,
            scores_json           = excluded.scores_json,
            features_json         = excluded.features_json,
            raw_metadata_json     = excluded.raw_metadata_json,
            corroboration_verdict = excluded.corroboration_verdict
        RETURNING id
        """,
        (
            source_pk,
            run_pk,
            item.get("summary"),
            item.get("one_line_takeaway"),
            surrogate.get("evidence_tier") or item.get("evidence_tier"),
            item.get("transcript_status"),
            item.get("comments_status"),
            dumps(scores),
            dumps(features),
            dumps(raw_metadata),
            item.get("corroboration_verdict"),
            observed_at,
        ),
    )
    row = cur.fetchone()
    return row[0]


def insert_comments(
    conn: sqlite3.Connection,
    snapshot_pk: int,
    source_comments: list[dict],
    *,
    persist_text: bool,
) -> int:
    count = 0
    for c in source_comments:
        if not isinstance(c, dict):
            continue
        comment_id = c.get("comment_id") or ""
        if not comment_id:
            continue
        raw_text: str | None = c.get("text")
        text = raw_text if persist_text else None
        digest = sha256_hex(raw_text)
        conn.execute(
            """
            INSERT OR IGNORE INTO comments (
                source_snapshot_id, comment_id, author, text, text_digest,
                like_count, published_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot_pk,
                comment_id,
                c.get("author"),
                text,
                digest,
                c.get("like_count"),
                c.get("published_at"),
            ),
        )
        count += 1
    return count


def insert_transcript(
    conn: sqlite3.Connection,
    snapshot_pk: int,
    item: dict,
    *,
    persist_text: bool,
    fetched_at: str | None = None,
) -> None:
    status = item.get("transcript_status") or "unavailable"
    raw_text: str | None = item.get("transcript")
    text = raw_text if persist_text else None
    digest = sha256_hex(raw_text)
    char_count = len(raw_text) if raw_text else None
    conn.execute(
        """
        INSERT OR REPLACE INTO transcripts (
            source_snapshot_id, status, text, text_digest, char_count, fetched_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (snapshot_pk, status, text, digest, char_count, fetched_at),
    )


def insert_text_surrogate(
    conn: sqlite3.Connection,
    snapshot_pk: int,
    surrogate: dict,
) -> None:
    primary_text: str | None = surrogate.get("primary_text")
    conn.execute(
        """
        INSERT OR REPLACE INTO text_surrogates (
            source_snapshot_id, primary_text, primary_text_source, text_digest,
            evidence_layers_json, evidence_tier, char_count,
            confidence_penalties_json, warnings_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            snapshot_pk,
            primary_text,
            surrogate.get("primary_text_source"),
            sha256_hex(primary_text),
            dumps(surrogate.get("evidence_layers") or []),
            surrogate.get("evidence_tier"),
            surrogate.get("char_count"),
            dumps(surrogate.get("confidence_penalties") or []),
            dumps(surrogate.get("warnings") or []),
        ),
    )


def insert_warnings(
    conn: sqlite3.Connection,
    run_pk: int,
    warnings: list,
) -> int:
    count = 0
    for w in warnings:
        if isinstance(w, dict):
            message = w.get("message") or str(w)
            kind = w.get("kind")
        else:
            message = str(w)
            kind = None
        conn.execute(
            "INSERT INTO warnings (run_id, message, kind) VALUES (?, ?, ?)",
            (run_pk, message, kind),
        )
        count += 1
    return count


def insert_artifacts(
    conn: sqlite3.Connection,
    run_pk: int,
    *,
    html_report_path: str | None,
    export_paths: dict[str, str],
    created_at: str,
) -> int:
    count = 0
    if html_report_path:
        conn.execute(
            "INSERT INTO artifacts (run_id, kind, path, created_at) VALUES (?, ?, ?, ?)",
            (run_pk, "html_report", html_report_path, created_at),
        )
        count += 1
    for kind, path in export_paths.items():
        conn.execute(
            "INSERT INTO artifacts (run_id, kind, path, created_at) VALUES (?, ?, ?, ?)",
            (run_pk, kind, path, created_at),
        )
        count += 1
    return count
