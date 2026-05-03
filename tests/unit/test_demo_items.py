"""Tests for the synthetic ScoredItem builder used by the demo report."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch

from social_research_probe.commands._demo_constants import DEMO_THEMES
from social_research_probe.commands._demo_items import build_demo_items

_FIXED_NOW = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)


def test_item_count():
    items = build_demo_items()
    assert len(items) == 12


def test_total_comments_in_range():
    items = build_demo_items()
    total = sum(len(item["comments"]) for item in items)
    assert 30 <= total <= 60


def test_total_source_comments_match_comments():
    items = build_demo_items()
    for item in items:
        assert len(item["source_comments"]) == len(item["comments"])


def test_all_required_transcript_statuses_present():
    items = build_demo_items()
    statuses = {item["transcript_status"] for item in items}
    required = {"available", "unavailable", "failed", "disabled", "not_attempted"}
    assert required.issubset(statuses)


def test_extra_transcript_statuses_covered():
    items = build_demo_items()
    statuses = {item["transcript_status"] for item in items}
    assert "timeout" in statuses
    assert "provider_blocked" in statuses


def test_all_comments_statuses_present():
    items = build_demo_items()
    statuses = {item["comments_status"] for item in items}
    assert statuses == {
        "not_attempted",
        "available",
        "unavailable",
        "failed",
        "disabled",
    }


def test_all_evidence_tiers_present():
    items = build_demo_items()
    tiers = {item["evidence_tier"] for item in items}
    assert tiers == {
        "metadata_only",
        "metadata_comments",
        "metadata_transcript",
        "metadata_comments_transcript",
        "metadata_external",
        "full",
    }


def test_source_classes_mixed():
    items = build_demo_items()
    classes = {item["source_class"] for item in items}
    assert {"primary", "secondary", "commentary", "unknown"}.issubset(classes)


def test_scores_in_unit_range():
    items = build_demo_items()
    for item in items:
        for key in ("trust", "trend", "opportunity", "overall"):
            value = item["scores"][key]
            assert 0.0 <= value <= 1.0


def test_each_item_has_required_fields():
    required = {
        "title",
        "channel",
        "url",
        "source_class",
        "scores",
        "features",
        "one_line_takeaway",
        "summary",
        "summary_source",
        "transcript",
        "transcript_status",
        "evidence_tier",
        "text_surrogate",
        "corroboration_verdict",
        "comments_status",
        "source_comments",
        "comments",
    }
    items = build_demo_items()
    for item in items:
        assert required.issubset(item.keys())


def test_text_surrogate_has_evidence_layers():
    items = build_demo_items()
    rich = [it for it in items if len(it["text_surrogate"]["evidence_layers"]) >= 3]
    assert len(rich) >= 3


def test_source_comments_have_engagement():
    items = build_demo_items()
    populated = [it for it in items if it["source_comments"]]
    assert len(populated) >= 3
    for item in populated:
        for sc in item["source_comments"]:
            assert "like_count" in sc
            assert "author" in sc
            assert "comment_id" in sc


def test_summaries_reference_themes():
    items = build_demo_items()
    joined = " ".join(item["summary"] for item in items)
    matched = [theme for theme in DEMO_THEMES if theme in joined]
    assert len(matched) >= 3


def test_deterministic_across_calls():
    with patch("social_research_probe.utils.claims.extractor.datetime") as mock_dt:
        mock_dt.now.return_value = _FIXED_NOW
        a = build_demo_items()
        b = build_demo_items()
    assert a == b


def test_corroboration_verdicts_mixed():
    items = build_demo_items()
    verdicts = {item["corroboration_verdict"] for item in items}
    assert {"verified", "partially_verified", "unverified"}.issubset(verdicts)


def test_urls_are_unique():
    items = build_demo_items()
    urls = [item["url"] for item in items]
    assert len(urls) == len(set(urls))


def test_transcript_text_present_when_status_available():
    items = build_demo_items()
    for item in items:
        if item["transcript_status"] == "available":
            assert item["transcript"]


def test_transcript_text_empty_when_status_not_available():
    items = build_demo_items()
    for item in items:
        if item["transcript_status"] != "available":
            assert item["transcript"] == ""


def test_summary_source_matches_transcript_presence():
    items = build_demo_items()
    for item in items:
        if item["transcript"]:
            assert item["summary_source"] == "transcript"
        else:
            assert item["summary_source"] == "description"


def test_zero_comment_items_have_empty_lists():
    items = build_demo_items()
    zero = [it for it in items if not it["comments"]]
    for item in zero:
        assert item["source_comments"] == []
