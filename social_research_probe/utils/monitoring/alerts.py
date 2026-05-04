"""Deterministic alert rule validation and evaluation."""

from __future__ import annotations

import json

from social_research_probe.utils.core.errors import ValidationError
from social_research_probe.utils.monitoring.defaults import (
    SUPPORTED_ALERT_METRICS,
    SUPPORTED_ALERT_OPERATORS,
    SUPPORTED_ALERT_SEVERITIES,
)
from social_research_probe.utils.monitoring.types import AlertRule, MatchedRule

_SEVERITY_RANK = {"info": 0, "warning": 1, "critical": 2}


def parse_alert_rule_json(raw: str) -> AlertRule:
    """Parse one alert rule JSON string and validate its shape."""
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValidationError(f"invalid alert rule JSON: {exc.msg}") from exc
    if not isinstance(parsed, dict):
        raise ValidationError("alert rule must be a JSON object")
    return validate_alert_rule(parsed)


def validate_alert_rule(rule: dict) -> AlertRule:
    """Validate one alert rule and return its normalized form."""
    metric = rule.get("metric")
    op = rule.get("op")
    if not isinstance(metric, str) or metric not in SUPPORTED_ALERT_METRICS:
        raise ValidationError(f"unsupported alert metric: {metric!r}")
    if not isinstance(op, str) or op not in SUPPORTED_ALERT_OPERATORS:
        raise ValidationError(f"unsupported alert operator: {op!r}")
    _validate_rule_value(metric, op, rule.get("value"))
    severity = rule.get("severity", "warning")
    if not isinstance(severity, str) or severity not in SUPPORTED_ALERT_SEVERITIES:
        raise ValidationError(f"unsupported alert severity: {severity!r}")
    title = rule.get("title", _default_title(metric))
    if not isinstance(title, str) or not title.strip():
        raise ValidationError("alert rule title must be a non-empty string")
    return AlertRule(metric=metric, op=op, value=rule["value"], severity=severity, title=title)


def validate_alert_rules(rules: list[dict]) -> list[AlertRule]:
    """Validate all alert rules."""
    return [validate_alert_rule(rule) for rule in rules]


def evaluate_alert_rules(
    comparison: dict, rules: list[dict], extra_metrics: dict[str, object] | None = None
) -> list[MatchedRule]:
    """Return validated rules that match a comparison result."""
    normalized = validate_alert_rules(rules)
    metrics = _metric_values(comparison, extra_metrics or {})
    matched: list[MatchedRule] = []
    for rule in normalized:
        actual = metrics[rule["metric"]]
        if _matches(actual, rule["op"], rule["value"]):
            matched.append(
                MatchedRule(
                    metric=rule["metric"],
                    op=rule["op"],
                    value=rule["value"],
                    severity=rule["severity"],
                    title=rule["title"],
                    actual=actual,
                )
            )
    return matched


def max_severity(rules: list[MatchedRule]) -> str:
    """Return the highest severity across matched rules."""
    if not rules:
        return "info"
    return max((r["severity"] for r in rules), key=lambda s: _SEVERITY_RANK.get(s, 0))


def build_alert_title(watch: dict, matched: list[MatchedRule]) -> str:
    """Build a research-monitoring alert title."""
    if len(matched) == 1:
        return matched[0]["title"]
    return f"{len(matched)} monitoring rules matched for {watch['topic']}"


def build_alert_message(watch: dict, matched: list[MatchedRule]) -> str:
    """Build a concise local monitoring alert message."""
    pieces = [f"{m['metric']} {m['op']} {m['value']} (actual: {m['actual']})" for m in matched]
    return f"Watch {watch['watch_id']} detected research changes: " + "; ".join(pieces)


def _validate_rule_value(metric: str, op: str, value: object) -> None:
    if op in {">=", ">", "<=", "<"} and not _is_number(value):
        raise ValidationError(f"alert metric {metric!r} with operator {op!r} needs a number")
    if op == "in" and not _is_non_empty_list(value):
        raise ValidationError(f"alert metric {metric!r} with operator 'in' needs a non-empty list")
    if op == "==" and value is None:
        raise ValidationError(f"alert metric {metric!r} with operator '==' needs a value")


def _metric_values(comparison: dict, extra: dict[str, object]) -> dict[str, object]:
    narrative_changes = comparison.get("narrative_changes") or []
    trends = comparison.get("trends") or []
    return {
        "new_narratives_count": _count_status(narrative_changes, "new"),
        "rising_risk_score": _max_delta(narrative_changes, "risk_change"),
        "growing_opportunity_score": _max_delta(narrative_changes, "opportunity_change"),
        "new_claims_count": _count_status(comparison.get("claim_changes") or [], "new"),
        "new_sources_count": _count_status(comparison.get("source_changes") or [], "new"),
        "claims_needing_review": extra.get("claims_needing_review", 0),
        "trend_signal_type": [t.get("signal_type") for t in trends if t.get("signal_type")],
        "narrative_type": [
            n.get("cluster_type") for n in narrative_changes if n.get("cluster_type")
        ],
    }


def _matches(actual: object, op: str, expected: object) -> bool:
    if op == "in":
        return _matches_in(actual, expected)
    if op == "==":
        return actual == expected
    if not (_is_number(actual) and _is_number(expected)):
        return False
    return _numeric_match(float(actual), op, float(expected))


def _matches_in(actual: object, expected: object) -> bool:
    if not isinstance(expected, list):
        return False
    if isinstance(actual, list):
        return any(item in expected for item in actual)
    return actual in expected


def _numeric_match(actual: float, op: str, expected: float) -> bool:
    if op == ">=":
        return actual >= expected
    if op == ">":
        return actual > expected
    if op == "<=":
        return actual <= expected
    if op == "<":
        return actual < expected
    return False


def _count_status(changes: list[dict], status: str) -> int:
    return sum(1 for change in changes if change.get("status") == status)


def _max_delta(changes: list[dict], key: str) -> float:
    values = [float(change.get(key) or 0.0) for change in changes]
    return max(values, default=0.0)


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_non_empty_list(value: object) -> bool:
    return isinstance(value, list) and len(value) > 0


def _default_title(metric: str) -> str:
    return metric.replace("_", " ").capitalize()
