"""Repository helpers for reading and writing srp.db tables."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid


def _normalize(obj: object) -> object:
    """Normalize a value before it is stored or compared.

    Persistence helpers keep database schema decisions at the storage boundary instead of spreading

    SQL-shaped data through the pipeline.

    Args:
        obj: Python object being serialized for storage.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            _normalize(
                obj={"title": "Example"},
            )
        Output:
            "AI safety"
    """
    if isinstance(obj, float):
        return round(obj, 6)
    if isinstance(obj, dict):
        return {str(k): _normalize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_normalize(v) for v in obj]
    return obj


def dumps(obj: object) -> str:
    """Document the dumps rule at the boundary where callers use it.

    Persistence helpers keep database schema decisions at the storage boundary instead of spreading

    SQL-shaped data through the pipeline.

    Args:
        obj: Python object being serialized for storage.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            dumps(
                obj={"title": "Example"},
            )
        Output:
            "AI safety"
    """
    return json.dumps(_normalize(obj), sort_keys=True, separators=(",", ":"))


def sha256_hex(text: str | None) -> str | None:
    """Create a SHA-256 hex digest for stable IDs.

    Persistence helpers keep SQL and schema details at the storage boundary instead of leaking them
    through pipeline code.

    Args:
        text: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
              to a provider.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            sha256_hex(
                text="This tool reduces latency by 30%.",
            )
        Output:
            "AI safety"
    """
    if text is None:
        return None
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def derive_source_key(item: dict) -> tuple[str, str]:
    """Derive source key from stable fields.

    Persistence helpers keep database schema decisions at the storage boundary instead of spreading
    SQL-shaped data through the pipeline.

    Args:
        item: Single source item, database row, or registry entry being transformed.

    Returns:
        Tuple whose positions are part of the public helper contract shown in the example.

    Examples:
        Input:
            derive_source_key(
                item={"title": "Example", "url": "https://youtu.be/demo"},
            )
        Output:
            ("AI safety", "Find unmet needs")
    """
    surrogate = item.get("text_surrogate") or {}
    platform = surrogate.get("platform") or "youtube"
    external_id = surrogate.get("source_id") or item.get("id") or ""
    if not external_id:
        url = item.get("url") or ""
        external_id = "url-" + hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
    return platform, str(external_id)


def derive_run_id(report: dict) -> str:
    """Derive run ID from stable fields.

    Persistence helpers keep database schema decisions at the storage boundary instead of spreading
    SQL-shaped data through the pipeline.

    Args:
        report: Research report dictionary being rendered, exported, or persisted.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            derive_run_id(
                report={"topic": "AI safety", "items_top_n": []},
            )
        Output:
            "AI safety"
    """
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
    """Insert run records into SQLite.

    Keeping SQL details here lets pipeline code work with project records instead of database
    plumbing.

    Args:
        conn: Open SQLite connection for the current transaction.
        run_id: Stable identifier for one research run.
        topic: Research topic text or existing topic list used for classification and suggestions.
        platform: Platform name, such as youtube or all, used to select config and pipeline
                  behavior.
        purpose_set: Purpose names attached to the report or persisted run.
        started_at: Run start timestamp written to persistence.
        finished_at: Run finish timestamp written to persistence.
        html_report_path: Filesystem location used to read, write, or resolve project data.
        output_dir: Filesystem location used to read, write, or resolve project data.
        export_paths: Filesystem location used to read, write, or resolve project data.
        warning_count: Count, database id, index, or limit that bounds the work being performed.
        exit_status: Final run status stored with the persisted run.
        config_snapshot: Configuration snapshot stored with the run for reproducibility.
        schema_version: Count, database id, index, or limit that bounds the work being performed.

    Returns:
        Integer count, limit, status code, or timeout used by the caller.

    Examples:
        Input:
            insert_run(
                conn=sqlite3.Connection(":memory:"),
                run_id="AI safety",
                topic="AI safety",
                platform="AI safety",
                purpose_set=["AI safety"],
                started_at="AI safety",
                finished_at="AI safety",
                html_report_path=Path("report.html"),
                output_dir=Path(".skill-data"),
                export_paths=Path("report.html"),
                warning_count=3,
                exit_status="AI safety",
                config_snapshot={"enabled": True},
                schema_version=3,
            )
        Output:
            5
    """
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
    """Insert or update source in SQLite.

    Keeping SQL details here lets pipeline code work with project records instead of database
    plumbing.

    Args:
        conn: Open SQLite connection for the current transaction.
        platform: Platform name, such as youtube or all, used to select config and pipeline
                  behavior.
        external_id: Provider-specific source id used for upsert matching.
        url: Stable source identifier or URL used to join records across stages and exports.
        title: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
               to a provider.
        description: Source text, prompt text, or raw value being parsed, normalized, classified, or
                     sent to a provider.
        channel: YouTube channel name, id, or classification map used for source labeling.
        source_class: Source-class label such as primary, secondary, commentary, or unknown.
        published_at: Source publication timestamp from the provider.
        now: Timestamp used for recency filtering, age calculations, or persisted audit metadata.

    Returns:
        Integer count, limit, status code, or timeout used by the caller.

    Examples:
        Input:
            upsert_source(
                conn=sqlite3.Connection(":memory:"),
                platform="AI safety",
                external_id="AI safety",
                url="https://youtu.be/abc123",
                title="This tool reduces latency by 30%.",
                description="This tool reduces latency by 30%.",
                channel="OpenAI",
                source_class="primary",
                published_at="AI safety",
                now=datetime(2026, 1, 1),
            )
        Output:
            5
    """
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
    """Insert snapshot records into SQLite.

    Keeping SQL details here lets pipeline code work with project records instead of database
    plumbing.

    Args:
        conn: Open SQLite connection for the current transaction.
        source_pk: Count, database id, index, or limit that bounds the work being performed.
        run_pk: Count, database id, index, or limit that bounds the work being performed.
        item: Single source item, database row, or registry entry being transformed.
        observed_at: Timestamp when the metric snapshot was recorded.

    Returns:
        Integer count, limit, status code, or timeout used by the caller.

    Examples:
        Input:
            insert_snapshot(
                conn=sqlite3.Connection(":memory:"),
                source_pk=3,
                run_pk=3,
                item={"title": "Example", "url": "https://youtu.be/demo"},
                observed_at="AI safety",
            )
        Output:
            5
    """
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
    """Insert comments records into SQLite.

    Keeping SQL details here lets pipeline code work with project records instead of database
    plumbing.

    Args:
        conn: Open SQLite connection for the current transaction.
        snapshot_pk: Count, database id, index, or limit that bounds the work being performed.
        source_comments: Comment records associated with the source snapshot.
        persist_text: Flag that selects the branch for this operation.

    Returns:
        Integer count, limit, status code, or timeout used by the caller.

    Examples:
        Input:
            insert_comments(
                conn=sqlite3.Connection(":memory:"),
                snapshot_pk=3,
                source_comments=["AI safety"],
                persist_text=True,
            )
        Output:
            5
    """
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
    """Insert transcript records into SQLite.

    Keeping SQL details here lets pipeline code work with project records instead of database
    plumbing.

    Args:
        conn: Open SQLite connection for the current transaction.
        snapshot_pk: Count, database id, index, or limit that bounds the work being performed.
        item: Single source item, database row, or registry entry being transformed.
        persist_text: Flag that selects the branch for this operation.
        fetched_at: Timestamp when provider text was fetched.

    Returns:
        None. The result is communicated through state mutation, file/database writes, output, or an
        exception.

    Examples:
        Input:
            insert_transcript(
                conn=sqlite3.Connection(":memory:"),
                snapshot_pk=3,
                item={"title": "Example", "url": "https://youtu.be/demo"},
                persist_text=True,
                fetched_at="AI safety",
            )
        Output:
            None
    """
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
    """Insert text surrogate records into SQLite.

    Keeping SQL details here lets pipeline code work with project records instead of database
    plumbing.

    Args:
        conn: Open SQLite connection for the current transaction.
        snapshot_pk: Count, database id, index, or limit that bounds the work being performed.
        surrogate: Text surrogate payload that represents the source content available for later
                   stages.

    Returns:
        None. The result is communicated through state mutation, file/database writes, output, or an
        exception.

    Examples:
        Input:
            insert_text_surrogate(
                conn=sqlite3.Connection(":memory:"),
                snapshot_pk=3,
                surrogate={"primary_text": "Demo transcript"},
            )
        Output:
            None
    """
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
    """Insert warnings records into SQLite.

    Keeping SQL details here lets pipeline code work with project records instead of database
    plumbing.

    Args:
        conn: Open SQLite connection for the current transaction.
        run_pk: Count, database id, index, or limit that bounds the work being performed.
        warnings: Warning or penalty records that explain reduced evidence quality.

    Returns:
        Integer count, limit, status code, or timeout used by the caller.

    Examples:
        Input:
            insert_warnings(
                conn=sqlite3.Connection(":memory:"),
                run_pk=3,
                warnings=["Transcript unavailable"],
            )
        Output:
            5
    """
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


def insert_claims(
    conn: sqlite3.Connection,
    run_pk: int,
    snapshot_pk: int,
    source_pk: int,
    claims: list,
    *,
    source_url: str,
    source_title: str,
    created_at: str,
) -> int:
    """Insert claims records into SQLite.

    Keeping SQL details here lets pipeline code work with project records instead of database
    plumbing.

    Args:
        conn: Open SQLite connection for the current transaction.
        run_pk: Count, database id, index, or limit that bounds the work being performed.
        snapshot_pk: Count, database id, index, or limit that bounds the work being performed.
        source_pk: Count, database id, index, or limit that bounds the work being performed.
        claims: Claim records being extracted, reviewed, persisted, or corroborated.
        source_url: Stable source identifier or URL used to join records across stages and exports.
        source_title: Human-readable source title stored with extracted claims or citations.
        created_at: Timestamp written with the created database record.

    Returns:
        Integer count, limit, status code, or timeout used by the caller.

    Examples:
        Input:
            insert_claims(
                conn=sqlite3.Connection(":memory:"),
                run_pk=3,
                snapshot_pk=3,
                source_pk=3,
                claims={"text": "The model reduces latency by 30%."},
                source_url="https://youtu.be/abc123",
                source_title="Example video",
                created_at="AI safety",
            )
        Output:
            5
    """
    count = 0
    for c in claims:
        if not isinstance(c, dict):
            continue
        claim_id = c.get("claim_id") or ""
        if not claim_id:
            continue
        conn.execute(
            """
            INSERT OR IGNORE INTO claims (
                claim_id, run_id, source_snapshot_id, source_id,
                source_url, source_title, claim_text, evidence_text,
                claim_type, entities_json, confidence, evidence_layer,
                evidence_tier, needs_corroboration, corroboration_status,
                contradiction_status, needs_review, uncertainty,
                extraction_method, source_sentence, position_in_text,
                context_before, context_after, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                claim_id,
                run_pk,
                snapshot_pk,
                source_pk,
                source_url,
                source_title,
                c.get("claim_text") or "",
                c.get("evidence_text"),
                c.get("claim_type"),
                dumps(c.get("entities") or []),
                c.get("confidence"),
                c.get("evidence_layer"),
                c.get("evidence_tier"),
                1 if c.get("needs_corroboration") else 0,
                c.get("corroboration_status"),
                c.get("contradiction_status"),
                1 if c.get("needs_review") else 0,
                c.get("uncertainty"),
                c.get("extraction_method"),
                c.get("source_sentence"),
                c.get("position_in_text"),
                c.get("context_before"),
                c.get("context_after"),
                created_at,
            ),
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
    """Insert artifacts records into SQLite.

    Keeping SQL details here lets pipeline code work with project records instead of database
    plumbing.

    Args:
        conn: Open SQLite connection for the current transaction.
        run_pk: Count, database id, index, or limit that bounds the work being performed.
        html_report_path: Filesystem location used to read, write, or resolve project data.
        export_paths: Filesystem location used to read, write, or resolve project data.
        created_at: Timestamp written with the created database record.

    Returns:
        Integer count, limit, status code, or timeout used by the caller.

    Examples:
        Input:
            insert_artifacts(
                conn=sqlite3.Connection(":memory:"),
                run_pk=3,
                html_report_path=Path("report.html"),
                export_paths=Path("report.html"),
                created_at="AI safety",
            )
        Output:
            5
    """
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
