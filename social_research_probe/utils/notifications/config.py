"""Resolve local notification configuration."""

from __future__ import annotations

from social_research_probe.utils.notifications.types import NotificationChannelConfig


def notifications_enabled(cfg: object) -> bool:
    """Return whether notification sending is globally enabled."""
    settings = _notification_settings(cfg)
    flag = settings.get("enabled", True)
    return bool(flag)


def default_channel_names(cfg: object) -> list[str]:
    """Return configured default notification channel names."""
    settings = _notification_settings(cfg)
    raw = settings.get("default_channels", ["file"])
    if not isinstance(raw, list):
        return ["file"]
    names = [item for item in raw if isinstance(item, str) and item.strip()]
    return names or ["file"]


def channel_config(cfg: object, channel: str) -> NotificationChannelConfig:
    """Return resolved config for one channel."""
    settings = _notification_settings(cfg)
    raw = settings.get(channel)
    data = dict(raw) if isinstance(raw, dict) else {}
    enabled = bool(data.pop("enabled", False))
    return {"kind": channel, "enabled": enabled, "config": data}


def _notification_settings(cfg: object) -> dict[str, object]:
    raw = getattr(cfg, "raw", {})
    if not isinstance(raw, dict):
        return {}
    settings = raw.get("notifications", {})
    return dict(settings) if isinstance(settings, dict) else {}
