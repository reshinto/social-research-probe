"""SQLite schema definition and forward-only migration infrastructure."""

from __future__ import annotations

import shutil
import sqlite3
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

SCHEMA_VERSION: int = 5

SCHEMA_DDL_V1: str = """\
CREATE TABLE IF NOT EXISTS schema_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS research_runs (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id               TEXT NOT NULL UNIQUE,
    topic                TEXT NOT NULL,
    platform             TEXT NOT NULL,
    purpose_set_json     TEXT NOT NULL DEFAULT '[]',
    started_at           TEXT NOT NULL,
    finished_at          TEXT,
    html_report_path     TEXT,
    output_dir           TEXT,
    export_paths_json    TEXT NOT NULL DEFAULT '{}',
    warning_count        INTEGER NOT NULL DEFAULT 0,
    exit_status          TEXT NOT NULL DEFAULT 'ok',
    config_snapshot_json TEXT NOT NULL DEFAULT '{}',
    schema_version       INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_runs_topic    ON research_runs(topic);
CREATE INDEX IF NOT EXISTS idx_runs_platform ON research_runs(platform);

CREATE TABLE IF NOT EXISTS sources (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    platform       TEXT NOT NULL,
    external_id    TEXT NOT NULL,
    url            TEXT NOT NULL,
    title          TEXT,
    description    TEXT,
    channel        TEXT,
    source_class   TEXT,
    published_at   TEXT,
    first_seen_at  TEXT NOT NULL,
    last_seen_at   TEXT NOT NULL,
    UNIQUE(platform, external_id)
);
CREATE INDEX IF NOT EXISTS idx_sources_url ON sources(url);

CREATE TABLE IF NOT EXISTS source_snapshots (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id             INTEGER NOT NULL REFERENCES sources(id)       ON DELETE CASCADE,
    run_id                INTEGER NOT NULL REFERENCES research_runs(id) ON DELETE CASCADE,
    summary               TEXT,
    one_line_takeaway     TEXT,
    evidence_tier         TEXT,
    transcript_status     TEXT,
    comments_status       TEXT,
    scores_json           TEXT NOT NULL DEFAULT '{}',
    features_json         TEXT NOT NULL DEFAULT '{}',
    raw_metadata_json     TEXT NOT NULL DEFAULT '{}',
    corroboration_verdict TEXT,
    observed_at           TEXT NOT NULL,
    UNIQUE(source_id, run_id)
);
CREATE INDEX IF NOT EXISTS idx_snap_run    ON source_snapshots(run_id);
CREATE INDEX IF NOT EXISTS idx_snap_source ON source_snapshots(source_id);
CREATE INDEX IF NOT EXISTS idx_snap_tier   ON source_snapshots(evidence_tier);

CREATE TABLE IF NOT EXISTS comments (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    source_snapshot_id INTEGER NOT NULL REFERENCES source_snapshots(id) ON DELETE CASCADE,
    comment_id         TEXT NOT NULL,
    author             TEXT,
    text               TEXT,
    text_digest        TEXT,
    like_count         INTEGER,
    published_at       TEXT,
    UNIQUE(source_snapshot_id, comment_id)
);
CREATE INDEX IF NOT EXISTS idx_comments_snap ON comments(source_snapshot_id);

CREATE TABLE IF NOT EXISTS transcripts (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    source_snapshot_id INTEGER NOT NULL UNIQUE REFERENCES source_snapshots(id) ON DELETE CASCADE,
    status             TEXT NOT NULL,
    text               TEXT,
    text_digest        TEXT,
    char_count         INTEGER,
    fetched_at         TEXT
);

CREATE TABLE IF NOT EXISTS text_surrogates (
    id                        INTEGER PRIMARY KEY AUTOINCREMENT,
    source_snapshot_id        INTEGER NOT NULL UNIQUE REFERENCES source_snapshots(id) ON DELETE CASCADE,
    primary_text              TEXT,
    primary_text_source       TEXT,
    text_digest               TEXT,
    evidence_layers_json      TEXT NOT NULL DEFAULT '[]',
    evidence_tier             TEXT,
    char_count                INTEGER,
    confidence_penalties_json TEXT NOT NULL DEFAULT '[]',
    warnings_json             TEXT NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS warnings (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id  INTEGER NOT NULL REFERENCES research_runs(id) ON DELETE CASCADE,
    message TEXT NOT NULL,
    kind    TEXT
);
CREATE INDEX IF NOT EXISTS idx_warnings_run ON warnings(run_id);

CREATE TABLE IF NOT EXISTS artifacts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id     INTEGER NOT NULL REFERENCES research_runs(id) ON DELETE CASCADE,
    kind       TEXT NOT NULL,
    path       TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_artifacts_run  ON artifacts(run_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_kind ON artifacts(kind);
"""

SCHEMA_DDL_V2: str = """\
CREATE TABLE IF NOT EXISTS claims (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    claim_id             TEXT NOT NULL,
    run_id               INTEGER NOT NULL REFERENCES research_runs(id) ON DELETE CASCADE,
    source_snapshot_id   INTEGER REFERENCES source_snapshots(id) ON DELETE CASCADE,
    source_id            INTEGER REFERENCES sources(id) ON DELETE CASCADE,
    source_url           TEXT,
    source_title         TEXT,
    claim_text           TEXT NOT NULL,
    evidence_text        TEXT,
    claim_type           TEXT,
    entities_json        TEXT NOT NULL DEFAULT '[]',
    confidence           REAL,
    evidence_layer       TEXT,
    evidence_tier        TEXT,
    needs_corroboration  INTEGER DEFAULT 0,
    corroboration_status TEXT,
    contradiction_status TEXT,
    needs_review         INTEGER DEFAULT 0,
    uncertainty          TEXT,
    extraction_method    TEXT,
    source_sentence      TEXT,
    position_in_text     INTEGER,
    context_before       TEXT,
    context_after        TEXT,
    created_at           TEXT NOT NULL,
    UNIQUE(source_snapshot_id, claim_id)
);
CREATE INDEX IF NOT EXISTS idx_claims_run    ON claims(run_id);
CREATE INDEX IF NOT EXISTS idx_claims_source ON claims(source_id);
CREATE INDEX IF NOT EXISTS idx_claims_type   ON claims(claim_type);
CREATE INDEX IF NOT EXISTS idx_claims_review ON claims(needs_review);
CREATE INDEX IF NOT EXISTS idx_claims_corrob ON claims(corroboration_status);
"""

SCHEMA_DDL_V3: str = """\
CREATE TABLE IF NOT EXISTS claim_reviews (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    claim_pk       INTEGER NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    claim_id       TEXT NOT NULL,
    run_id         INTEGER NOT NULL REFERENCES research_runs(id) ON DELETE CASCADE,
    review_status  TEXT NOT NULL DEFAULT 'unreviewed',
    review_note    TEXT,
    importance     TEXT,
    quality_score  REAL,
    reviewed_at    TEXT NOT NULL,
    UNIQUE(claim_pk)
);
CREATE INDEX IF NOT EXISTS idx_claim_reviews_claim ON claim_reviews(claim_pk);
CREATE INDEX IF NOT EXISTS idx_claim_reviews_status ON claim_reviews(review_status);

CREATE TABLE IF NOT EXISTS claim_notes (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    claim_pk   INTEGER NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    claim_id   TEXT NOT NULL,
    run_id     INTEGER REFERENCES research_runs(id) ON DELETE CASCADE,
    note_text  TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_claim_notes_claim ON claim_notes(claim_pk);
"""

SCHEMA_DDL_V4: str = """\
CREATE TABLE IF NOT EXISTS narrative_clusters (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    narrative_id                TEXT NOT NULL,
    run_id                      INTEGER NOT NULL REFERENCES research_runs(id) ON DELETE CASCADE,
    title                       TEXT NOT NULL,
    summary                     TEXT,
    cluster_type                TEXT NOT NULL,
    entities_json               TEXT NOT NULL DEFAULT '[]',
    keywords_json               TEXT NOT NULL DEFAULT '[]',
    evidence_tiers_json         TEXT NOT NULL DEFAULT '[]',
    corroboration_statuses_json TEXT NOT NULL DEFAULT '[]',
    representative_claims_json  TEXT NOT NULL DEFAULT '[]',
    source_count                INTEGER NOT NULL DEFAULT 0,
    claim_count                 INTEGER NOT NULL DEFAULT 0,
    confidence                  REAL,
    opportunity_score           REAL,
    risk_score                  REAL,
    contradiction_count         INTEGER NOT NULL DEFAULT 0,
    needs_review_count          INTEGER NOT NULL DEFAULT 0,
    created_at                  TEXT NOT NULL,
    UNIQUE(run_id, narrative_id)
);
CREATE INDEX IF NOT EXISTS idx_narr_run ON narrative_clusters(run_id);
CREATE INDEX IF NOT EXISTS idx_narr_type ON narrative_clusters(cluster_type);
CREATE INDEX IF NOT EXISTS idx_narr_opportunity ON narrative_clusters(opportunity_score);
CREATE INDEX IF NOT EXISTS idx_narr_risk ON narrative_clusters(risk_score);

CREATE TABLE IF NOT EXISTS narrative_claims (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    narrative_pk INTEGER NOT NULL REFERENCES narrative_clusters(id) ON DELETE CASCADE,
    claim_id     TEXT NOT NULL,
    UNIQUE(narrative_pk, claim_id)
);
CREATE INDEX IF NOT EXISTS idx_narr_claims_narr ON narrative_claims(narrative_pk);

CREATE TABLE IF NOT EXISTS narrative_sources (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    narrative_pk INTEGER NOT NULL REFERENCES narrative_clusters(id) ON DELETE CASCADE,
    source_id    TEXT NOT NULL,
    source_url   TEXT,
    UNIQUE(narrative_pk, source_id)
);
CREATE INDEX IF NOT EXISTS idx_narr_sources_narr ON narrative_sources(narrative_pk);
"""

SCHEMA_DDL_V5: str = """\
CREATE TABLE IF NOT EXISTS watches (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    watch_id           TEXT NOT NULL UNIQUE,
    topic              TEXT NOT NULL,
    platform           TEXT NOT NULL,
    purposes_json      TEXT NOT NULL DEFAULT '[]',
    enabled            INTEGER NOT NULL DEFAULT 1,
    interval           TEXT,
    alert_rules_json   TEXT NOT NULL DEFAULT '[]',
    output_dir         TEXT,
    created_at         TEXT NOT NULL,
    updated_at         TEXT NOT NULL,
    last_run_at        TEXT,
    last_target_run_id TEXT
);
CREATE INDEX IF NOT EXISTS idx_watches_enabled ON watches(enabled);
CREATE INDEX IF NOT EXISTS idx_watches_topic_platform ON watches(topic, platform);

CREATE TABLE IF NOT EXISTS watch_runs (
    id                        INTEGER PRIMARY KEY AUTOINCREMENT,
    watch_run_id              TEXT NOT NULL UNIQUE,
    watch_id                  TEXT NOT NULL REFERENCES watches(watch_id) ON DELETE CASCADE,
    baseline_run_id           TEXT,
    target_run_id             TEXT,
    started_at                TEXT NOT NULL,
    finished_at               TEXT,
    status                    TEXT NOT NULL,
    error_kind                TEXT,
    error_message             TEXT,
    comparison_artifacts_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_watch_runs_watch ON watch_runs(watch_id);
CREATE INDEX IF NOT EXISTS idx_watch_runs_target ON watch_runs(target_run_id);
CREATE INDEX IF NOT EXISTS idx_watch_runs_started ON watch_runs(started_at);

CREATE TABLE IF NOT EXISTS alert_events (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id             TEXT NOT NULL UNIQUE,
    watch_id             TEXT NOT NULL REFERENCES watches(watch_id) ON DELETE CASCADE,
    baseline_run_id      TEXT,
    target_run_id        TEXT,
    created_at           TEXT NOT NULL,
    severity             TEXT,
    title                TEXT,
    message              TEXT,
    matched_rules_json   TEXT NOT NULL DEFAULT '[]',
    trend_signals_json   TEXT NOT NULL DEFAULT '[]',
    artifact_paths_json  TEXT NOT NULL DEFAULT '{}',
    acknowledged         INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_alert_events_watch ON alert_events(watch_id);
CREATE INDEX IF NOT EXISTS idx_alert_events_target ON alert_events(target_run_id);
CREATE INDEX IF NOT EXISTS idx_alert_events_created ON alert_events(created_at);
CREATE INDEX IF NOT EXISTS idx_alert_events_ack ON alert_events(acknowledged);
"""

MIGRATIONS: list[Callable[[sqlite3.Connection], None]] = [
    lambda conn: conn.executescript(SCHEMA_DDL_V1),
    lambda conn: conn.executescript(SCHEMA_DDL_V2),
    lambda conn: conn.executescript(SCHEMA_DDL_V3),
    lambda conn: conn.executescript(SCHEMA_DDL_V4),
    lambda conn: conn.executescript(SCHEMA_DDL_V5),
]


def _read_version(conn: sqlite3.Connection) -> int:
    """Read the SQLite schema version from the database.

    Persistence helpers keep SQL and schema details at the storage boundary instead of leaking them
    through pipeline code.

    Args:
        conn: Open SQLite connection for the current transaction.

    Returns:
        Integer count, limit, status code, or timeout used by the caller.

    Examples:
        Input:
            _read_version(
                conn=sqlite3.Connection(":memory:"),
            )
        Output:
            5
    """
    try:
        row = conn.execute("SELECT value FROM schema_meta WHERE key = 'version'").fetchone()
    except sqlite3.OperationalError:
        return 0
    return int(row[0]) if row else 0


def _backup_db(db_path: Path) -> None:
    """Document the backup db rule at the boundary where callers use it.

    Persistence helpers keep database schema decisions at the storage boundary instead of spreading

    SQL-shaped data through the pipeline.

    Args:
        db_path: Filesystem location used to read, write, or resolve project data.

    Returns:
        None. The result is communicated through state mutation, file/database writes, output, or an
        exception.

    Examples:
        Input:
            _backup_db(
                db_path=Path("srp.db"),
            )
        Output:
            None
    """
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    backup = db_path.with_suffix(f".db.bak.{ts}")
    shutil.copy2(db_path, backup)


def ensure_schema(conn: sqlite3.Connection, db_path: Path | None = None) -> int:
    """Ensure schema exists before callers depend on it.

    Keeping SQL details here lets pipeline code work with project records instead of database
    plumbing.

    Args:
        conn: Open SQLite connection for the current transaction.
        db_path: Filesystem location used to read, write, or resolve project data.

    Returns:
        Integer count, limit, status code, or timeout used by the caller.

    Examples:
        Input:
            ensure_schema(
                conn=sqlite3.Connection(":memory:"),
                db_path=Path("srp.db"),
            )
        Output:
            5
    """
    current = _read_version(conn)

    if current > SCHEMA_VERSION:
        raise RuntimeError(f"DB schema v{current} is newer than this binary (v{SCHEMA_VERSION})")

    if current == SCHEMA_VERSION:
        return current

    if current > 0 and db_path is not None and db_path.exists():
        _backup_db(db_path)

    for migration in MIGRATIONS[current:]:
        migration(conn)

    conn.execute(
        "INSERT OR REPLACE INTO schema_meta(key, value) VALUES ('version', ?)",
        (str(SCHEMA_VERSION),),
    )
    conn.commit()
    return SCHEMA_VERSION
