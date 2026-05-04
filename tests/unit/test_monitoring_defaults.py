"""Tests for monitor default definitions."""

from __future__ import annotations

from social_research_probe.utils.monitoring.alerts import validate_alert_rules
from social_research_probe.utils.monitoring.defaults import DEFAULT_ALERT_RULES


def test_default_alert_rules_are_valid() -> None:
    assert validate_alert_rules(DEFAULT_ALERT_RULES) == DEFAULT_ALERT_RULES
