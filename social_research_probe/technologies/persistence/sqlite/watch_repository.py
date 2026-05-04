"""SQLite helpers for local watch definitions, watch runs, and alert events."""

from __future__ import annotations

import json
import sqlite3

from social_research_probe.technologies.persistence.sqlite.repository import dumps


def _rows_to_dicts(cursor: sqlite3.Cursor) -> list[dict]:
    cols = [desc[0] for desc in cursor.description]
    return [_decode_row(dict(zip(cols, row, strict=True))) for row in cursor.fetchall()]


def _row_to_dict(cursor: sqlite3.Cursor) -> dict | None:
    row = cursor.fetchone()
    if row is None:
        return None
    cols = [desc[0] for desc in cursor.description]
    return _decode_row(dict(zip(cols, row, strict=True)))


def _loads(raw: object, fallback: object) -> object:
    if not isinstance(raw, str) or raw == "":
        return fallback
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return fallback


def _decode_row(row: dict) -> dict:
    for source, target, fallback in [
        ("purposes_json", "purposes", []),
        ("alert_rules_json", "alert_rules", []),
        ("matched_rules_json", "matched_rules", []),
        ("trend_signals_json", "trend_signals", []),
        ("artifact_paths_json", "artifact_paths", {}),
        ("comparison_artifacts_json", "comparison_artifacts", {}),
    ]:
        if source in row:
            row[target] = _loads(row.pop(source), fallback)
    if "enabled" in row:
        row["enabled"] = bool(row["enabled"])
    if "acknowledged" in row:
        row["acknowledged"] = bool(row["acknowledged"])
    return row


def insert_watch(
    conn: sqlite3.Connection,
    *,
    watch_id: str,
    topic: str,
    platform: str,
    purposes: list[str],
    enabled: bool,
    interval: str | None,
    alert_rules: list[dict],
    output_dir: str | None,
    created_at: str,
    updated_at: str,
) -> int:
    cur = conn.execute(
        """
        INSERT INTO watches (
            watch_id, topic, platform, purposes_json, enabled, interval,
            alert_rules_json, output_dir, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            watch_id,
            topic,
            platform,
            dumps(purposes),
            int(enabled),
            interval,
            dumps(alert_rules),
            output_dir,
            created_at,
            updated_at,
        ),
    )
    return cur.lastrowid  # type: ignore[return-value]


def get_watch(conn: sqlite3.Connection, watch_id: str) -> dict | None:
    cur = conn.execute("SELECT * FROM watches WHERE watch_id = ?", (watch_id,))
    return _row_to_dict(cur)


def list_watches(conn: sqlite3.Connection, *, enabled_only: bool = False) -> list[dict]:
    if enabled_only:
        cur = conn.execute("SELECT * FROM watches WHERE enabled = 1 ORDER BY created_at, id")
    else:
        cur = conn.execute("SELECT * FROM watches ORDER BY created_at, id")
    return _rows_to_dicts(cur)


def remove_watch(conn: sqlite3.Connection, watch_id: str) -> int:
    cur = conn.execute("DELETE FROM watches WHERE watch_id = ?", (watch_id,))
    return cur.rowcount


def update_watch_after_run(
    conn: sqlite3.Connection,
    *,
    watch_id: str,
    last_run_at: str,
    last_target_run_id: str,
    updated_at: str,
) -> None:
    conn.execute(
        """
        UPDATE watches
        SET last_run_at = ?, last_target_run_id = ?, updated_at = ?
        WHERE watch_id = ?
        """,
        (last_run_at, last_target_run_id, updated_at, watch_id),
    )


def insert_watch_run(
    conn: sqlite3.Connection,
    *,
    watch_run_id: str,
    watch_id: str,
    baseline_run_id: str | None,
    target_run_id: str | None,
    started_at: str,
    finished_at: str | None,
    status: str,
    error_kind: str | None,
    error_message: str | None,
    comparison_artifacts: dict[str, str],
) -> int:
    cur = conn.execute(
        """
        INSERT INTO watch_runs (
            watch_run_id, watch_id, baseline_run_id, target_run_id, started_at,
            finished_at, status, error_kind, error_message, comparison_artifacts_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            watch_run_id,
            watch_id,
            baseline_run_id,
            target_run_id,
            started_at,
            finished_at,
            status,
            error_kind,
            error_message,
            dumps(comparison_artifacts),
        ),
    )
    return cur.lastrowid  # type: ignore[return-value]


def latest_successful_watch_run(conn: sqlite3.Connection, watch_id: str) -> dict | None:
    cur = conn.execute(
        """
        SELECT * FROM watch_runs
        WHERE watch_id = ? AND status = 'success' AND target_run_id IS NOT NULL
        ORDER BY started_at DESC, id DESC
        LIMIT 1
        """,
        (watch_id,),
    )
    return _row_to_dict(cur)


def insert_alert_event(
    conn: sqlite3.Connection,
    *,
    alert_id: str,
    watch_id: str,
    baseline_run_id: str | None,
    target_run_id: str | None,
    created_at: str,
    severity: str,
    title: str,
    message: str,
    matched_rules: list[dict],
    trend_signals: list[dict],
    artifact_paths: dict[str, str],
    acknowledged: bool = False,
) -> int:
    cur = conn.execute(
        """
        INSERT INTO alert_events (
            alert_id, watch_id, baseline_run_id, target_run_id, created_at,
            severity, title, message, matched_rules_json, trend_signals_json,
            artifact_paths_json, acknowledged
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            alert_id,
            watch_id,
            baseline_run_id,
            target_run_id,
            created_at,
            severity,
            title,
            message,
            dumps(matched_rules),
            dumps(trend_signals),
            dumps(artifact_paths),
            int(acknowledged),
        ),
    )
    return cur.lastrowid  # type: ignore[return-value]


def list_alert_events(
    conn: sqlite3.Connection, *, watch_id: str | None = None, limit: int = 100
) -> list[dict]:
    if watch_id:
        cur = conn.execute(
            "SELECT * FROM alert_events WHERE watch_id = ? ORDER BY created_at DESC LIMIT ?",
            (watch_id, limit),
        )
    else:
        cur = conn.execute("SELECT * FROM alert_events ORDER BY created_at DESC LIMIT ?", (limit,))
    return _rows_to_dicts(cur)
