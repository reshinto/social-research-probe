"""Dispatch alert notifications and record delivery attempts."""

from __future__ import annotations

import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path

from social_research_probe.utils.notifications.channels import (
    send_console_notification,
    send_file_notification,
    send_telegram_notification,
)
from social_research_probe.utils.notifications.config import (
    channel_config,
    default_channel_names,
    notifications_enabled,
)
from social_research_probe.utils.notifications.types import (
    ChannelSendResult,
    NotificationChannelConfig,
    NotificationDelivery,
    NotificationMessage,
)


def dispatch_alert_notifications(
    conn: sqlite3.Connection,
    cfg: object,
    alerts: list[dict],
    channels: list[str] | None = None,
) -> list[NotificationDelivery]:
    """Send alert notifications through configured local channels."""
    if not alerts or not notifications_enabled(cfg):
        return []
    names = channels if channels is not None else default_channel_names(cfg)
    deliveries: list[NotificationDelivery] = []
    for alert in alerts:
        message = message_from_alert(alert)
        deliveries.extend(_dispatch_message(conn, cfg, message, names))
    return deliveries


def message_from_alert(alert: dict) -> NotificationMessage:
    """Build a notification message from a persisted alert event."""
    return {
        "title": str(alert.get("title") or "Monitoring Alert"),
        "body": str(alert.get("message") or ""),
        "severity": str(alert.get("severity") or "info"),
        "watch_id": str(alert.get("watch_id") or ""),
        "alert_id": str(alert.get("alert_id") or ""),
        "created_at": str(alert.get("created_at") or _now()),
        "artifact_paths": _string_map(alert.get("artifact_paths") or {}),
    }


def _dispatch_message(
    conn: sqlite3.Connection, cfg: object, message: NotificationMessage, channels: list[str]
) -> list[NotificationDelivery]:
    deliveries: list[NotificationDelivery] = []
    for name in channels:
        if _already_sent(conn, message, name):
            continue
        channel = channel_config(cfg, name)
        result = _send_to_channel(message, channel, Path(getattr(cfg, "data_dir", ".")))
        delivery = _delivery_from_result(message, name, result)
        _record_delivery(conn, delivery)
        deliveries.append(delivery)
    return deliveries


def _send_to_channel(
    message: NotificationMessage, channel: NotificationChannelConfig, data_dir: Path
) -> ChannelSendResult:
    try:
        if channel["kind"] == "console":
            return send_console_notification(message, channel)
        if channel["kind"] == "file":
            return send_file_notification(message, channel, data_dir)
        if channel["kind"] == "telegram":
            return send_telegram_notification(message, channel)
        return _failed_result(f"unknown notification channel: {channel['kind']}")
    except Exception as exc:
        return _failed_result(f"{exc.__class__.__name__}: {exc}")


def _already_sent(conn: sqlite3.Connection, message: NotificationMessage, channel: str) -> bool:
    from social_research_probe.technologies.persistence.sqlite.watch_repository import (
        has_successful_delivery,
    )

    try:
        return has_successful_delivery(conn, alert_id=message["alert_id"], channel=channel)
    except sqlite3.Error:
        return False


def _record_delivery(conn: sqlite3.Connection, delivery: NotificationDelivery) -> None:
    from social_research_probe.technologies.persistence.sqlite.watch_repository import (
        insert_notification_delivery,
    )

    try:
        with conn:
            insert_notification_delivery(conn, **delivery)
    except Exception:
        return


def _delivery_from_result(
    message: NotificationMessage, channel: str, result: ChannelSendResult
) -> NotificationDelivery:
    return {
        "delivery_id": _new_id(),
        "alert_id": message["alert_id"],
        "watch_id": message["watch_id"],
        "channel": channel,
        "status": result["status"],
        "error_message": result["error_message"],
        "sent_at": _now(),
        "message_title": message["title"],
        "artifact_paths": result["artifact_paths"],
    }


def _failed_result(error_message: str) -> ChannelSendResult:
    return {"status": "failed", "error_message": error_message, "artifact_paths": {}}


def _string_map(raw: object) -> dict[str, str]:
    if not isinstance(raw, dict):
        return {}
    return {str(key): str(value) for key, value in raw.items()}


def _new_id() -> str:
    return f"delivery-{uuid.uuid4().hex[:12]}"


def _now() -> str:
    return datetime.now(UTC).isoformat()
