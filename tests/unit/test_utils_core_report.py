"""Tests for utils.core.report."""

from __future__ import annotations

from social_research_probe.utils.core.report import unwrap_report, wrap_report


def test_wrap_report_returns_envelope():
    payload = {"foo": "bar"}
    env = wrap_report(payload, "synthesis")
    assert env == {"kind": "synthesis", "report": payload}


def test_unwrap_envelope_extracts_inner_report():
    payload = {"foo": "bar"}
    env = {"kind": "synthesis", "report": payload}
    assert unwrap_report(env) is payload


def test_unwrap_passthrough_when_not_envelope():
    payload = {"some": "data"}
    assert unwrap_report(payload) is payload


def test_unwrap_passthrough_when_kind_not_string():
    payload = {"kind": 123, "report": {"x": 1}}
    assert unwrap_report(payload) is payload


def test_unwrap_passthrough_when_report_not_dict():
    payload = {"kind": "synthesis", "report": "not-a-dict"}
    assert unwrap_report(payload) is payload


def test_unwrap_non_dict_input():
    assert unwrap_report("string") == "string"
    assert unwrap_report([1, 2]) == [1, 2]
