"""Tests for SQLite watch repository helpers."""

from __future__ import annotations

import sqlite3

from social_research_probe.technologies.persistence.sqlite.schema import ensure_schema
from social_research_probe.technologies.persistence.sqlite.watch_repository import (
    _loads,
    get_watch,
    has_successful_delivery,
    insert_alert_event,
    insert_notification_delivery,
    insert_watch,
    insert_watch_run,
    latest_successful_watch_run,
    list_alert_events,
    list_notification_deliveries,
    list_watches,
    remove_watch,
    update_watch_after_run,
)


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys=ON")
    ensure_schema(conn)
    return conn


def test_watch_crud_round_trips_json() -> None:
    conn = _conn()
    insert_watch(
        conn,
        watch_id="watch-ai",
        topic="AI agents",
        platform="youtube",
        purposes=["latest-news"],
        enabled=True,
        interval="daily",
        alert_rules=[{"metric": "new_claims_count", "op": ">=", "value": 2}],
        output_dir=None,
        created_at="2026-01-01T00:00:00",
        updated_at="2026-01-01T00:00:00",
    )
    watch = get_watch(conn, "watch-ai")
    assert watch["purposes"] == ["latest-news"]
    assert watch["enabled"] is True
    assert len(list_watches(conn)) == 1
    assert len(list_watches(conn, enabled_only=True)) == 1
    assert get_watch(conn, "missing") is None
    assert remove_watch(conn, "watch-ai") == 1
    conn.close()


def test_watch_run_records_success_and_failure_details() -> None:
    conn = _conn()
    _insert_min_watch(conn)
    insert_watch_run(
        conn,
        watch_run_id="wr1",
        watch_id="watch-ai",
        baseline_run_id=None,
        target_run_id="run-1",
        started_at="2026-01-01T00:00:00",
        finished_at="2026-01-01T00:01:00",
        status="success",
        error_kind=None,
        error_message=None,
        comparison_artifacts={"summary_json": "/tmp/x.json"},
    )
    insert_watch_run(
        conn,
        watch_run_id="wr2",
        watch_id="watch-ai",
        baseline_run_id="run-1",
        target_run_id=None,
        started_at="2026-01-02T00:00:00",
        finished_at="2026-01-02T00:01:00",
        status="failed",
        error_kind="ValidationError",
        error_message="missing run id",
        comparison_artifacts={},
    )
    assert latest_successful_watch_run(conn, "watch-ai")["target_run_id"] == "run-1"
    conn.close()


def test_alert_events_round_trip_json() -> None:
    conn = _conn()
    _insert_min_watch(conn)
    insert_alert_event(
        conn,
        alert_id="alert-1",
        watch_id="watch-ai",
        baseline_run_id="run-1",
        target_run_id="run-2",
        created_at="2026-01-02T00:00:00",
        severity="warning",
        title="New claims detected",
        message="Watch detected research changes",
        matched_rules=[{"metric": "new_claims_count", "actual": 4}],
        trend_signals=[{"signal_type": "rising_risk"}],
        artifact_paths={"alert_json": "/tmp/alert.json"},
    )
    alert = list_alert_events(conn)[0]
    assert list_alert_events(conn, watch_id="watch-ai")[0]["alert_id"] == "alert-1"
    assert alert["matched_rules"][0]["metric"] == "new_claims_count"
    assert alert["acknowledged"] is False
    conn.close()


def test_notification_deliveries_round_trip_json_and_filters() -> None:
    conn = _conn()
    insert_notification_delivery(
        conn,
        delivery_id="delivery-1",
        alert_id="alert-1",
        watch_id="watch-ai",
        channel="file",
        status="sent",
        error_message=None,
        sent_at="2026-01-02T00:00:00",
        message_title="New claims detected",
        artifact_paths={"notification_markdown": "/tmp/notification.md"},
    )
    delivery = list_notification_deliveries(conn, alert_id="alert-1")[0]
    assert delivery["artifact_paths"]["notification_markdown"].endswith("notification.md")
    assert has_successful_delivery(conn, alert_id="alert-1", channel="file") is True
    assert list_notification_deliveries(conn, watch_id="watch-ai")[0]["delivery_id"] == "delivery-1"
    assert list_notification_deliveries(conn, channel="file")[0]["status"] == "sent"
    assert list_notification_deliveries(conn, status="sent")[0]["watch_id"] == "watch-ai"
    assert has_successful_delivery(conn, alert_id="missing", channel="file") is False
    conn.close()


def test_loads_fallback_paths() -> None:
    assert _loads("", []) == []
    assert _loads(None, {}) == {}
    assert _loads("{", []) == []


def test_update_watch_after_run() -> None:
    conn = _conn()
    _insert_min_watch(conn)
    update_watch_after_run(
        conn,
        watch_id="watch-ai",
        last_run_at="2026-01-03T00:00:00",
        last_target_run_id="run-3",
        updated_at="2026-01-03T00:00:00",
    )
    assert get_watch(conn, "watch-ai")["last_target_run_id"] == "run-3"
    conn.close()


def _insert_min_watch(conn: sqlite3.Connection) -> None:
    insert_watch(
        conn,
        watch_id="watch-ai",
        topic="AI agents",
        platform="youtube",
        purposes=["latest-news"],
        enabled=True,
        interval=None,
        alert_rules=[],
        output_dir=None,
        created_at="2026-01-01T00:00:00",
        updated_at="2026-01-01T00:00:00",
    )
