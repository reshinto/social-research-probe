"""Default local monitoring rules."""

from __future__ import annotations

from social_research_probe.utils.monitoring.types import AlertRule

DEFAULT_ALERT_RULES: list[AlertRule] = [
    {
        "metric": "new_narratives_count",
        "op": ">=",
        "value": 1,
        "severity": "warning",
        "title": "New research narrative detected",
    },
    {
        "metric": "new_claims_count",
        "op": ">=",
        "value": 5,
        "severity": "warning",
        "title": "New claims detected",
    },
    {
        "metric": "claims_needing_review",
        "op": ">=",
        "value": 3,
        "severity": "warning",
        "title": "Claims need review",
    },
    {
        "metric": "trend_signal_type",
        "op": "in",
        "value": ["emerging_narrative", "rising_risk", "growing_opportunity"],
        "severity": "info",
        "title": "Research trend signal detected",
    },
]


SUPPORTED_ALERT_METRICS: frozenset[str] = frozenset(
    {
        "new_narratives_count",
        "rising_risk_score",
        "growing_opportunity_score",
        "new_claims_count",
        "new_sources_count",
        "claims_needing_review",
        "trend_signal_type",
        "narrative_type",
    }
)

SUPPORTED_ALERT_OPERATORS: frozenset[str] = frozenset({">=", ">", "<=", "<", "==", "in"})
SUPPORTED_ALERT_SEVERITIES: frozenset[str] = frozenset({"info", "warning", "critical"})
