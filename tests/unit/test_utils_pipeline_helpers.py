"""Tests for utils.pipeline.helpers."""

from __future__ import annotations

from social_research_probe.services import ServiceResult, TechResult
from social_research_probe.utils.pipeline.helpers import (
    collect_divergence_warnings,
    dict_items,
    first_tech_output,
)

T = "real transcript text"


def test_no_items_returns_empty():
    assert collect_divergence_warnings([], threshold=0.5) == []


def test_item_below_threshold_not_included():
    items = [{"title": "Low", "summary_divergence": 0.3, "transcript": T}]
    assert collect_divergence_warnings(items, threshold=0.5) == []


def test_item_at_threshold_not_included():
    items = [{"title": "At", "summary_divergence": 0.5, "transcript": T}]
    assert collect_divergence_warnings(items, threshold=0.5) == []


def test_item_above_threshold_included():
    items = [{"title": "High", "summary_divergence": 0.8, "transcript": T}]
    result = collect_divergence_warnings(items, threshold=0.5)
    assert len(result) == 1
    assert "High" in result[0]
    assert "0.80" in result[0]


def test_title_truncated_to_80_chars():
    long_title = "A" * 100
    items = [{"title": long_title, "summary_divergence": 0.9, "transcript": T}]
    result = collect_divergence_warnings(items, threshold=0.5)
    assert "A" * 80 in result[0]
    assert "A" * 81 not in result[0]


def test_missing_title_falls_back_to_untitled():
    items = [{"summary_divergence": 0.9, "transcript": T}]
    result = collect_divergence_warnings(items, threshold=0.5)
    assert "untitled" in result[0]


def test_none_title_falls_back_to_untitled():
    items = [{"title": None, "summary_divergence": 0.9, "transcript": T}]
    result = collect_divergence_warnings(items, threshold=0.5)
    assert "untitled" in result[0]


def test_non_dict_item_skipped():
    items = ["not-a-dict", 42, None]
    assert collect_divergence_warnings(items, threshold=0.0) == []


def test_missing_divergence_key_skipped():
    items = [{"title": "No divergence key", "transcript": T}]
    assert collect_divergence_warnings(items, threshold=0.0) == []


def test_multiple_items_only_above_threshold_included():
    items = [
        {"title": "Low", "summary_divergence": 0.2, "transcript": T},
        {"title": "High", "summary_divergence": 0.9, "transcript": T},
        {"title": "Also high", "summary_divergence": 0.7, "transcript": T},
    ]
    result = collect_divergence_warnings(items, threshold=0.5)
    assert len(result) == 2
    titles = " ".join(result)
    assert "High" in titles
    assert "Also high" in titles
    assert "Low" not in titles


def test_missing_transcript_no_warning():
    items = [{"title": "X", "summary_divergence": 0.9}]
    assert collect_divergence_warnings(items, threshold=0.5) == []


def test_empty_transcript_no_warning():
    items = [{"title": "X", "summary_divergence": 0.9, "transcript": ""}]
    assert collect_divergence_warnings(items, threshold=0.5) == []


def test_whitespace_transcript_no_warning():
    items = [{"title": "X", "summary_divergence": 0.9, "transcript": "   \n  "}]
    assert collect_divergence_warnings(items, threshold=0.5) == []


def test_status_unavailable_no_warning():
    items = [
        {
            "title": "X",
            "summary_divergence": 0.9,
            "transcript": T,
            "transcript_status": "unavailable",
        }
    ]
    assert collect_divergence_warnings(items, threshold=0.5) == []


def test_status_failed_no_warning():
    items = [
        {"title": "X", "summary_divergence": 0.9, "transcript": T, "transcript_status": "failed"}
    ]
    assert collect_divergence_warnings(items, threshold=0.5) == []


def test_status_disabled_no_warning():
    items = [
        {"title": "X", "summary_divergence": 0.9, "transcript": T, "transcript_status": "disabled"}
    ]
    assert collect_divergence_warnings(items, threshold=0.5) == []


def test_no_status_with_transcript_warns():
    items = [{"title": "X", "summary_divergence": 0.9, "transcript": T}]
    result = collect_divergence_warnings(items, threshold=0.5)
    assert len(result) == 1
    assert "X" in result[0]


def test_status_available_with_transcript_warns():
    items = [
        {"title": "X", "summary_divergence": 0.9, "transcript": T, "transcript_status": "available"}
    ]
    result = collect_divergence_warnings(items, threshold=0.5)
    assert len(result) == 1


def test_low_divergence_with_transcript_no_warning():
    items = [{"title": "X", "summary_divergence": 0.1, "transcript": T}]
    assert collect_divergence_warnings(items, threshold=0.5) == []


def test_dict_items_filters_non_dict_values():
    assert dict_items([{"a": 1}, None, "x", {"b": 2}]) == [{"a": 1}, {"b": 2}]


def test_first_tech_output_returns_matching_output_type():
    result = ServiceResult(
        service_name="svc",
        input_key="key",
        tech_results=[
            TechResult("a", None, "nope", success=True),
            TechResult("b", None, {"ok": True}, success=False),
        ],
    )
    assert first_tech_output(result, dict) == {"ok": True}


def test_first_tech_output_can_require_success():
    result = ServiceResult(
        service_name="svc",
        input_key="key",
        tech_results=[
            TechResult("a", None, {"skip": True}, success=False),
            TechResult("b", None, {"ok": True}, success=True),
        ],
    )
    assert first_tech_output(result, dict, require_success=True) == {"ok": True}


def test_first_tech_output_can_require_truthy():
    result = ServiceResult(
        service_name="svc",
        input_key="key",
        tech_results=[
            TechResult("a", None, {}, success=True),
            TechResult("b", None, {"ok": True}, success=True),
        ],
    )
    assert first_tech_output(result, dict, require_truthy=True) == {"ok": True}


def test_first_tech_output_returns_none_without_match():
    result = ServiceResult(
        service_name="svc",
        input_key="key",
        tech_results=[TechResult("a", None, "nope", success=True)],
    )
    assert first_tech_output(result, dict) is None


def test_first_tech_output_handles_objects_without_tech_results():
    assert first_tech_output(object(), dict) is None
