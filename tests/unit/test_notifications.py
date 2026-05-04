"""Tests for local notification channels, dispatch, and CLI."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest

from social_research_probe.commands import NotifySubcommand
from social_research_probe.commands import notify as notify_cmd
from social_research_probe.technologies.persistence.sqlite.schema import ensure_schema
from social_research_probe.technologies.persistence.sqlite.watch_repository import (
    list_notification_deliveries,
)
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
from social_research_probe.utils.notifications.dispatcher import (
    dispatch_alert_notifications,
    message_from_alert,
)


class _Cfg:
    def __init__(self, tmp_path: Path, notifications: dict | None = None) -> None:
        self.data_dir = tmp_path
        self.database_path = tmp_path / "srp.db"
        self.raw = {
            "database": {"enabled": True},
            "notifications": notifications if notifications is not None else _notifications(),
        }


class _Response:
    def __init__(self, status: int = 200) -> None:
        self.status = status

    def raise_for_status(self) -> None:
        if self.status >= 400:
            raise httpx.HTTPStatusError("telegram failed", request=None, response=None)


@pytest.fixture(autouse=True)
def _block_http(monkeypatch: pytest.MonkeyPatch) -> None:
    import social_research_probe.utils.notifications.channels as channels_mod

    def blocked_post(*args: object, **kwargs: object) -> object:
        raise AssertionError("real Telegram HTTP is blocked in tests")

    monkeypatch.setattr(channels_mod.httpx, "post", blocked_post)


def _notifications() -> dict:
    return {
        "enabled": True,
        "default_channels": ["file"],
        "console": {"enabled": True},
        "file": {"enabled": True, "output_dir": "notices"},
        "telegram": {
            "enabled": False,
            "bot_token_env": "TELEGRAM_BOT_TOKEN",
            "chat_id_env": "TELEGRAM_CHAT_ID",
            "timeout_seconds": 10,
        },
    }


def _message() -> dict:
    return {
        "title": "New claims",
        "body": "Watch detected changes.",
        "severity": "warning",
        "watch_id": "watch-ai",
        "alert_id": "alert-1",
        "created_at": "2026-01-01T00:00:00+00:00",
        "artifact_paths": {"alert_markdown": "/tmp/alert.md"},
    }


def _alert() -> dict:
    msg = _message()
    return {
        "alert_id": msg["alert_id"],
        "watch_id": msg["watch_id"],
        "created_at": msg["created_at"],
        "severity": msg["severity"],
        "title": msg["title"],
        "message": msg["body"],
        "artifact_paths": msg["artifact_paths"],
    }


def _conn(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys=ON")
    ensure_schema(conn)
    return conn


def _args(**kwargs: object) -> argparse.Namespace:
    defaults = {"notify_cmd": NotifySubcommand.TEST, "channel": "file", "output": "text"}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def test_notification_config_defaults_and_fallbacks(tmp_path: Path) -> None:
    cfg = _Cfg(tmp_path)
    assert notifications_enabled(cfg) is True
    assert default_channel_names(cfg) == ["file"]
    assert channel_config(cfg, "file")["enabled"] is True
    bad = _Cfg(tmp_path, {"enabled": False, "default_channels": "bad"})
    assert notifications_enabled(bad) is False
    assert default_channel_names(bad) == ["file"]
    assert channel_config(bad, "missing") == {"kind": "missing", "enabled": False, "config": {}}
    cfg = _Cfg(tmp_path)
    cfg.raw = []
    assert notifications_enabled(cfg) is True


def test_console_notification_prints_and_disabled_skips(capsys: object) -> None:
    result = send_console_notification(
        _message(), {"kind": "console", "enabled": True, "config": {}}
    )
    empty = _message()
    empty["body"] = ""
    empty_result = send_console_notification(
        empty, {"kind": "console", "enabled": True, "config": {}}
    )
    skipped = send_console_notification(
        _message(), {"kind": "console", "enabled": False, "config": {}}
    )
    out = capsys.readouterr().out
    assert "[WARNING] New claims" in out
    assert result["status"] == "sent"
    assert empty_result["status"] == "sent"
    assert skipped["status"] == "skipped"


def test_file_notification_writes_markdown_and_disabled_skips(tmp_path: Path) -> None:
    channel = {"kind": "file", "enabled": True, "config": {"output_dir": "notices"}}
    result = send_file_notification(_message(), channel, tmp_path)
    path = Path(result["artifact_paths"]["notification_markdown"])
    assert path.exists()
    assert path.parent == tmp_path / "notices"
    content = path.read_text(encoding="utf-8")
    assert "Watch detected changes." in content
    assert "## Artifacts" in content
    assert "`alert_markdown`: `/tmp/alert.md`" in content
    tick_message = _message()
    tick_message["alert_id"] = "alert-backtick"
    tick_message["artifact_paths"] = {"alert`markdown": "/tmp/alert`one.md"}
    tick_result = send_file_notification(tick_message, channel, tmp_path)
    tick_content = Path(tick_result["artifact_paths"]["notification_markdown"]).read_text(
        encoding="utf-8"
    )
    assert "`` alert`markdown ``: `` /tmp/alert`one.md ``" in tick_content
    default_result = send_file_notification(
        _message(), {"kind": "file", "enabled": True, "config": {"output_dir": ""}}, tmp_path
    )
    assert (
        Path(default_result["artifact_paths"]["notification_markdown"]).parent.name
        == "notifications"
    )
    skipped = send_file_notification(
        _message(), {"kind": "file", "enabled": False, "config": {}}, tmp_path
    )
    assert skipped["status"] == "skipped"


def test_telegram_disabled_and_missing_env_fail_cleanly(monkeypatch: pytest.MonkeyPatch) -> None:
    disabled = send_telegram_notification(
        _message(), {"kind": "telegram", "enabled": False, "config": {}}
    )
    enabled = {"kind": "telegram", "enabled": True, "config": {}}
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    missing = send_telegram_notification(_message(), enabled)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "secret-token")
    missing_chat = send_telegram_notification(_message(), enabled)
    assert disabled["status"] == "skipped"
    assert missing["status"] == "failed"
    assert "TELEGRAM_BOT_TOKEN" in str(missing["error_message"])
    assert "TELEGRAM_CHAT_ID" in str(missing_chat["error_message"])


def test_telegram_success_and_http_error_are_mocked(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict] = []

    def fake_post(url: str, json: dict, timeout: float) -> _Response:
        calls.append({"url": url, "json": json, "timeout": timeout})
        return _Response()

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "secret-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat-1")
    monkeypatch.setattr("social_research_probe.utils.notifications.channels.httpx.post", fake_post)
    config = {
        "bot_token_env": "TELEGRAM_BOT_TOKEN",
        "chat_id_env": "TELEGRAM_CHAT_ID",
        "timeout_seconds": 0,
    }
    result = send_telegram_notification(
        _message(), {"kind": "telegram", "enabled": True, "config": config}
    )
    assert result["status"] == "sent"
    assert calls[0]["timeout"] == 10.0

    def failing_post(url: str, json: dict, timeout: float) -> _Response:
        return _Response(status=500)

    monkeypatch.setattr(
        "social_research_probe.utils.notifications.channels.httpx.post", failing_post
    )
    failed = send_telegram_notification(
        _message(), {"kind": "telegram", "enabled": True, "config": config}
    )
    assert failed["status"] == "failed"


def test_dispatcher_records_file_delivery_and_skips_duplicate(tmp_path: Path) -> None:
    cfg = _Cfg(tmp_path)
    conn = _conn(cfg.database_path)
    try:
        first = dispatch_alert_notifications(conn, cfg, [_alert()], ["file"])
        second = dispatch_alert_notifications(conn, cfg, [_alert()], ["file"])
        rows = list_notification_deliveries(conn)
    finally:
        conn.close()
    assert first[0]["status"] == "sent"
    assert second == []
    assert rows[0]["channel"] == "file"


def test_dispatcher_records_failures_and_blocks_real_http(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = _Cfg(tmp_path, _notifications() | {"telegram": {"enabled": True}})
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "secret-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat-1")
    conn = _conn(cfg.database_path)
    try:
        deliveries = dispatch_alert_notifications(conn, cfg, [_alert()], ["telegram", "unknown"])
        rows = list_notification_deliveries(conn, status="failed")
    finally:
        conn.close()
    assert len(deliveries) == 2
    assert len(rows) == 2
    assert all("secret-token" not in str(row.get("error_message")) for row in rows)


def test_dispatcher_global_disabled_and_minimal_alert(tmp_path: Path) -> None:
    cfg = _Cfg(tmp_path, {"enabled": False, "default_channels": []})
    conn = _conn(cfg.database_path)
    try:
        assert dispatch_alert_notifications(conn, cfg, [{}], None) == []
        assert message_from_alert({})["title"] == "Monitoring Alert"
        assert message_from_alert({"artifact_paths": ["not", "a", "dict"]})["artifact_paths"] == {}
    finally:
        conn.close()


def test_dispatcher_closed_db_does_not_raise(tmp_path: Path) -> None:
    cfg = _Cfg(tmp_path)
    conn = _conn(cfg.database_path)
    conn.close()
    deliveries = dispatch_alert_notifications(conn, cfg, [_alert()], ["file"])
    assert deliveries[0]["status"] == "sent"


def test_notify_test_cli_file_console_and_json(tmp_path: Path, capsys: object) -> None:
    cfg = _Cfg(tmp_path)
    with patch("social_research_probe.config.load_active_config", return_value=cfg):
        assert notify_cmd.run(_args(channel="file")) == 0
        assert notify_cmd.run(_args(channel="console")) == 0
    json_cfg = _Cfg(tmp_path / "json")
    with patch("social_research_probe.config.load_active_config", return_value=json_cfg):
        assert notify_cmd.run(_args(channel="file", output="json")) == 0
    out = capsys.readouterr().out
    assert "file sent" in out
    assert "console sent" in out
    assert '"channel": "file"' in out


def test_notify_test_cli_failed_delivery_returns_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: object
) -> None:
    cfg = _Cfg(tmp_path, _notifications() | {"telegram": {"enabled": True}})
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    with patch("social_research_probe.config.load_active_config", return_value=cfg):
        assert notify_cmd.run(_args(channel="telegram")) == 2
    out = capsys.readouterr().out
    assert "telegram failed" in out
    assert "TELEGRAM_BOT_TOKEN" in out


def test_notify_test_cli_no_deliveries_no_action_errors_and_db_disabled(
    tmp_path: Path, capsys: object
) -> None:
    disabled = _Cfg(tmp_path / "disabled", {"enabled": False})
    with patch("social_research_probe.config.load_active_config", return_value=disabled):
        assert notify_cmd.run(_args(channel="file")) == 0
    assert "No notification delivery attempted." in capsys.readouterr().out

    parser = argparse.ArgumentParser(prog="srp notify")
    with patch.object(parser, "print_help") as print_help:
        assert notify_cmd.run(_args(notify_cmd=None, _notify_parser=parser)) == 0
    print_help.assert_called_once()
    assert notify_cmd.run(_args(notify_cmd=None, _notify_parser=None)) == 0
    assert notify_cmd.run(_args(notify_cmd="bogus")) == 2
    cfg = _Cfg(tmp_path)
    cfg.raw["database"]["enabled"] = False
    with patch("social_research_probe.config.load_active_config", return_value=cfg):
        with pytest.raises(Exception, match=r"database\.enabled=true"):
            notify_cmd.run(_args())
