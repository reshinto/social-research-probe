"""Typed data contracts for watches, alert rules, and alert events."""

from __future__ import annotations

from typing import Literal, TypedDict

AlertOperator = Literal[">=", ">", "<=", "<", "==", "in"]
AlertSeverity = Literal["info", "warning", "critical"]
WatchRunStatus = Literal["success", "failed", "skipped"]


class AlertRule(TypedDict, total=False):
    """User-defined rule evaluated against a run comparison."""

    metric: str
    op: AlertOperator
    value: object
    severity: AlertSeverity
    title: str


class MatchedRule(TypedDict):
    """Validated alert rule that matched a comparison result."""

    metric: str
    op: AlertOperator
    value: object
    severity: AlertSeverity
    title: str
    actual: object


class WatchDefinition(TypedDict, total=False):
    """Persisted local watch definition."""

    watch_id: str
    topic: str
    platform: str
    purposes: list[str]
    enabled: bool
    interval: str | None
    alert_rules: list[AlertRule]
    output_dir: str | None
    created_at: str
    updated_at: str
    last_run_at: str | None
    last_target_run_id: str | None


class WatchRunRecord(TypedDict, total=False):
    """One attempted execution of a watch."""

    watch_run_id: str
    watch_id: str
    baseline_run_id: str | None
    target_run_id: str | None
    started_at: str
    finished_at: str | None
    status: WatchRunStatus
    error_kind: str | None
    error_message: str | None
    comparison_artifacts: dict[str, str]


class AlertEvent(TypedDict, total=False):
    """Persisted alert emitted by a watch run."""

    alert_id: str
    watch_id: str
    baseline_run_id: str | None
    target_run_id: str | None
    created_at: str
    severity: AlertSeverity
    title: str
    message: str
    matched_rules: list[MatchedRule]
    trend_signals: list[dict]
    artifact_paths: dict[str, str]
    acknowledged: bool
