"""Local notification channel implementations."""

from __future__ import annotations

import os
import re
from pathlib import Path

import httpx

from social_research_probe.utils.notifications.types import (
    ChannelSendResult,
    DeliveryStatus,
    NotificationChannelConfig,
    NotificationMessage,
)


def send_console_notification(
    message: NotificationMessage, channel: NotificationChannelConfig
) -> ChannelSendResult:
    """Print a concise notification summary to stdout."""
    if not channel["enabled"]:
        return _result("skipped", "console notification channel is disabled")
    print(f"[{message['severity'].upper()}] {message['title']}")
    print(f"watch={message['watch_id']} alert={message['alert_id']}")
    if message["body"]:
        print(message["body"])
    return _result("sent", None)


def send_file_notification(
    message: NotificationMessage, channel: NotificationChannelConfig, data_dir: Path
) -> ChannelSendResult:
    """Write one local Markdown notification file."""
    if not channel["enabled"]:
        return _result("skipped", "file notification channel is disabled")
    output_dir = _file_output_dir(channel, data_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / _notification_filename(message)
    path.write_text(_format_markdown(message), encoding="utf-8")
    return _result("sent", None, {"notification_markdown": str(path)})


def send_telegram_notification(
    message: NotificationMessage, channel: NotificationChannelConfig
) -> ChannelSendResult:
    """Send one Telegram notification when configured."""
    if not channel["enabled"]:
        return _result("skipped", "telegram notification channel is disabled")
    token, chat_id, error = _telegram_credentials(channel)
    if error is not None:
        return _result("failed", error)
    try:
        _post_telegram_message(str(token), str(chat_id), _telegram_text(message), channel)
    except httpx.HTTPError as exc:
        return _result("failed", f"Telegram delivery failed: {exc.__class__.__name__}")
    return _result("sent", None)


def _post_telegram_message(
    token: str, chat_id: str, text: str, channel: NotificationChannelConfig
) -> None:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    response = httpx.post(
        url,
        json={"chat_id": chat_id, "text": text},
        timeout=_telegram_timeout(channel),
    )
    response.raise_for_status()


def _telegram_credentials(
    channel: NotificationChannelConfig,
) -> tuple[str | None, str | None, str | None]:
    token_env = _config_str(channel, "bot_token_env", "TELEGRAM_BOT_TOKEN")
    chat_env = _config_str(channel, "chat_id_env", "TELEGRAM_CHAT_ID")
    token = os.environ.get(token_env)
    chat_id = os.environ.get(chat_env)
    if not token:
        return None, None, f"missing Telegram bot token env var: {token_env}"
    if not chat_id:
        return None, None, f"missing Telegram chat ID env var: {chat_env}"
    return token, chat_id, None


def _telegram_timeout(channel: NotificationChannelConfig) -> float:
    raw = channel["config"].get("timeout_seconds", 10)
    if isinstance(raw, (int, float)) and not isinstance(raw, bool) and raw > 0:
        return float(raw)
    return 10.0


def _telegram_text(message: NotificationMessage) -> str:
    return "\n".join(
        [
            f"[{message['severity'].upper()}] {message['title']}",
            f"Watch: {message['watch_id']}",
            f"Alert: {message['alert_id']}",
            message["body"],
        ]
    ).strip()


def _file_output_dir(channel: NotificationChannelConfig, data_dir: Path) -> Path:
    raw = channel["config"].get("output_dir", "")
    if isinstance(raw, str) and raw.strip():
        path = Path(raw).expanduser()
        return path if path.is_absolute() else data_dir / path
    return data_dir / "notifications"


def _notification_filename(message: NotificationMessage) -> str:
    watch = _safe_token(message["watch_id"])
    alert = _safe_token(message["alert_id"])
    ts = _safe_token(message["created_at"])
    return f"notification-{watch}-{alert}-{ts}.md"


def _safe_token(value: str) -> str:
    token = re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-")
    return token[:80] or "notification"


def _format_markdown(message: NotificationMessage) -> str:
    lines = [
        f"# {message['title']}",
        "",
        f"- Severity: `{message['severity']}`",
        f"- Watch: `{message['watch_id']}`",
        f"- Alert: `{message['alert_id']}`",
        f"- Created: `{message['created_at']}`",
        "",
        message["body"],
    ]
    if message["artifact_paths"]:
        lines.extend(["", "## Artifacts"])
        for name, path in sorted(message["artifact_paths"].items()):
            lines.append(f"- {_inline_code(name)}: {_inline_code(path)}")
    return "\n".join(lines).rstrip() + "\n"


def _inline_code(value: str) -> str:
    clean = value.replace("\r", " ").replace("\n", " ")
    if "`" not in clean:
        return f"`{clean}`"
    return f"`` {clean} ``"


def _config_str(channel: NotificationChannelConfig, key: str, default: str) -> str:
    raw = channel["config"].get(key, default)
    return raw if isinstance(raw, str) and raw.strip() else default


def _result(
    status: DeliveryStatus,
    error_message: str | None,
    artifact_paths: dict[str, str] | None = None,
) -> ChannelSendResult:
    return {
        "status": status,
        "error_message": error_message,
        "artifact_paths": artifact_paths or {},
    }
