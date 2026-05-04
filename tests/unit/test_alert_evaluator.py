"""Tests for deterministic monitor alert evaluation."""

from __future__ import annotations

import pytest

from social_research_probe.utils.core.errors import ValidationError
from social_research_probe.utils.monitoring.alerts import (
    _matches,
    _numeric_match,
    build_alert_message,
    build_alert_title,
    evaluate_alert_rules,
    max_severity,
    parse_alert_rule_json,
)


def _comparison() -> dict:
    return {
        "source_changes": [{"status": "new"}, {"status": "repeated"}],
        "claim_changes": [{"status": "new"}, {"status": "new"}],
        "narrative_changes": [
            {"status": "new", "cluster_type": "risk", "risk_change": 0.0},
            {
                "status": "repeated",
                "cluster_type": "opportunity",
                "risk_change": 0.2,
                "opportunity_change": 0.3,
            },
        ],
        "trends": [{"signal_type": "rising_risk"}],
    }


def test_numeric_rule_matches() -> None:
    rules = [{"metric": "new_claims_count", "op": ">=", "value": 2, "severity": "warning"}]
    matched = evaluate_alert_rules(_comparison(), rules)
    assert matched[0]["metric"] == "new_claims_count"
    assert matched[0]["actual"] == 2


def test_in_rule_matches_trend_signal() -> None:
    rules = [{"metric": "trend_signal_type", "op": "in", "value": ["rising_risk"]}]
    matched = evaluate_alert_rules(_comparison(), rules)
    assert len(matched) == 1


def test_extra_metric_claims_needing_review() -> None:
    rules = [{"metric": "claims_needing_review", "op": ">=", "value": 3}]
    matched = evaluate_alert_rules(_comparison(), rules, {"claims_needing_review": 3})
    assert len(matched) == 1


def test_invalid_rule_metric_fails_clearly() -> None:
    with pytest.raises(ValidationError, match="unsupported alert metric"):
        evaluate_alert_rules(_comparison(), [{"metric": "price", "op": ">=", "value": 1}])


def test_parse_alert_rule_json_requires_object() -> None:
    with pytest.raises(ValidationError, match="JSON object"):
        parse_alert_rule_json("[]")


def test_parse_alert_rule_json_valid() -> None:
    rule = parse_alert_rule_json('{"metric":"new_claims_count","op":">=","value":2}')
    assert rule["metric"] == "new_claims_count"


def test_parse_alert_rule_json_reports_decode_error() -> None:
    with pytest.raises(ValidationError, match="invalid alert rule JSON"):
        parse_alert_rule_json("{")


@pytest.mark.parametrize(
    ("rule", "message"),
    [
        ({"metric": "new_claims_count", "op": "bad", "value": 1}, "unsupported alert operator"),
        ({"metric": "new_claims_count", "op": ">=", "value": "x"}, "needs a number"),
        ({"metric": "trend_signal_type", "op": "in", "value": []}, "non-empty list"),
        ({"metric": "new_claims_count", "op": "==", "value": None}, "needs a value"),
        (
            {"metric": "new_claims_count", "op": ">=", "value": 1, "severity": "urgent"},
            "unsupported alert severity",
        ),
        (
            {"metric": "new_claims_count", "op": ">=", "value": 1, "title": ""},
            "non-empty string",
        ),
    ],
)
def test_invalid_rule_shapes_fail_clearly(rule: dict, message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        evaluate_alert_rules(_comparison(), [rule])


def test_default_title_and_no_match_path() -> None:
    rules = [{"metric": "new_claims_count", "op": ">", "value": 10}]
    assert evaluate_alert_rules(_comparison(), rules) == []


def test_all_numeric_operators() -> None:
    comparison = {"claim_changes": [{"status": "new"}]}
    rules = [
        {"metric": "new_claims_count", "op": ">", "value": 0},
        {"metric": "new_claims_count", "op": "<=", "value": 1},
        {"metric": "new_claims_count", "op": "<", "value": 2},
        {"metric": "new_claims_count", "op": "==", "value": 1},
    ]
    assert len(evaluate_alert_rules(comparison, rules)) == 4


def test_in_operator_scalar_and_invalid_expected() -> None:
    assert _matches("risk", "in", ["risk"]) is True
    assert _matches("risk", "in", "risk") is False


def test_numeric_match_rejects_non_numbers_and_unknown_operator() -> None:
    assert _matches("1", ">=", 1) is False
    assert _numeric_match(1.0, "!=", 1.0) is False


def test_alert_title_message_and_severity_helpers() -> None:
    watch = {"watch_id": "watch-ai", "topic": "AI agents"}
    matched = evaluate_alert_rules(
        _comparison(),
        [
            {"metric": "new_claims_count", "op": ">=", "value": 2, "severity": "critical"},
            {"metric": "trend_signal_type", "op": "in", "value": ["rising_risk"]},
        ],
    )
    assert max_severity([]) == "info"
    assert max_severity(matched) == "critical"
    assert build_alert_title(watch, matched[:1]) == matched[0]["title"]
    assert build_alert_title(watch, matched).startswith("2 monitoring rules")
    assert "detected research changes" in build_alert_message(watch, matched)
