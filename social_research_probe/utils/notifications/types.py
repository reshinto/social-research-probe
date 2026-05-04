"""Typed contracts for local notification delivery."""

from __future__ import annotations

from typing import Literal, TypedDict

DeliveryStatus = Literal["sent", "failed", "skipped"]


class NotificationMessage(TypedDict):
    """Message sent through one notification channel."""

    title: str
    body: str
    severity: str
    watch_id: str
    alert_id: str
    created_at: str
    artifact_paths: dict[str, str]


class NotificationChannelConfig(TypedDict):
    """Resolved settings for one notification channel."""

    kind: str
    enabled: bool
    config: dict[str, object]


class NotificationDelivery(TypedDict):
    """Auditable delivery attempt result."""

    delivery_id: str
    alert_id: str
    watch_id: str
    channel: str
    status: DeliveryStatus
    error_message: str | None
    sent_at: str
    message_title: str
    artifact_paths: dict[str, str]


class ChannelSendResult(TypedDict):
    """Result returned by one channel sender before DB persistence."""

    status: DeliveryStatus
    error_message: str | None
    artifact_paths: dict[str, str]
