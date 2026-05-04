"""srp notify subcommand: test local notification channels."""

from __future__ import annotations

import argparse
import json
import uuid
from datetime import UTC, datetime

from social_research_probe.utils.core.errors import ValidationError
from social_research_probe.utils.core.exit_codes import ExitCode


def _test(args: argparse.Namespace) -> int:
    from social_research_probe.utils.notifications.dispatcher import dispatch_alert_notifications

    conn, cfg = _open_db()
    try:
        deliveries = dispatch_alert_notifications(conn, cfg, [_test_alert()], [args.channel])
    finally:
        conn.close()
    _print_deliveries(deliveries, args)
    if any(delivery.get("status") == "failed" for delivery in deliveries):
        return ExitCode.ERROR
    return ExitCode.SUCCESS


def _open_db() -> tuple[object, object]:
    from social_research_probe.config import load_active_config
    from social_research_probe.technologies.persistence.sqlite.connection import open_connection
    from social_research_probe.technologies.persistence.sqlite.schema import ensure_schema

    cfg = load_active_config()
    db_cfg = cfg.raw.get("database") or {}
    if not db_cfg.get("enabled", True):
        raise ValidationError("notify test requires database.enabled=true")
    conn = open_connection(cfg.database_path)
    ensure_schema(conn, db_path=cfg.database_path)
    return conn, cfg


def _test_alert() -> dict:
    now = datetime.now(UTC).isoformat()
    return {
        "alert_id": f"alert-test-{uuid.uuid4().hex[:8]}",
        "watch_id": "watch-test",
        "created_at": now,
        "severity": "info",
        "title": "Notification test",
        "message": "This is a local Social Research Probe notification test.",
        "artifact_paths": {},
    }


def _print_deliveries(deliveries: list[dict], args: argparse.Namespace) -> None:
    if getattr(args, "output", "text") == "json":
        print(json.dumps(deliveries, indent=2, default=str))
        return
    if not deliveries:
        print("No notification delivery attempted.")
        return
    for delivery in deliveries:
        print(_delivery_line(delivery))


def _delivery_line(delivery: dict) -> str:
    channel = delivery.get("channel") or "unknown"
    status = delivery.get("status") or "unknown"
    error = delivery.get("error_message")
    return f"{channel} {status}: {error}" if error else f"{channel} {status}"


def run(args: argparse.Namespace) -> int:
    """Dispatch notify subcommands."""
    from social_research_probe.commands import NotifySubcommand

    if not getattr(args, "notify_cmd", None):
        parser = getattr(args, "_notify_parser", None)
        if parser:
            parser.print_help()
        return ExitCode.SUCCESS
    if args.notify_cmd == NotifySubcommand.TEST:
        return _test(args)
    return ExitCode.ERROR
