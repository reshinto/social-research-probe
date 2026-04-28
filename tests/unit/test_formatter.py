"""Tests for synthesizing.formatter."""

from __future__ import annotations

from social_research_probe.services.synthesizing.synthesis.helpers import formatter


def _basic_report(**overrides):
    base = {
        "topic": "ai",
        "platform": "youtube",
        "purpose_set": ["career"],
        "items_top_n": [],
        "source_validation_summary": {},
        "platform_engagement_summary": "",
        "evidence_summary": "",
        "stats_summary": {"highlights": [], "low_confidence": False},
        "chart_captions": [],
        "warnings": [],
    }
    base.update(overrides)
    return base


def test_build_report():
    out = formatter.build_report(
        topic="ai",
        platform="youtube",
        purpose_set=["career"],
        items_top_n=[],
        source_validation_summary={},
        platform_engagement_summary="",
        evidence_summary="",
        stats_summary={},
        chart_captions=[],
        warnings=[],
    )
    assert out["topic"] == "ai"


def test_render_sections_no_items():
    out = formatter.render_sections_1_9(_basic_report())
    assert "no items returned" in out


def test_render_sections_with_items_warnings_charts_stats():
    items = [
        {
            "channel": "Ch",
            "url": "https://x",
            "title": "T1",
            "source_class": "primary",
            "scores": {"trust": 0.9, "trend": 0.8, "opportunity": 0.7, "overall": 0.85},
            "one_line_takeaway": "tk",
        }
    ]
    report = _basic_report(
        items_top_n=items,
        source_validation_summary={
            "validated": 5,
            "partially": 1,
            "unverified": 0,
            "low_trust": 0,
            "primary": 5,
            "secondary": 1,
            "commentary": 0,
            "notes": "ok",
        },
        platform_engagement_summary="x; y",
        evidence_summary="a; b",
        stats_summary={"highlights": ["Mean overall: 0.5 — value"], "low_confidence": True},
        chart_captions=["c1", "c2"],
        warnings=["w1"],
    )
    out = formatter.render_sections_1_9(report)
    assert (
        "T1" in out
        and "Mean" in out
        and "Charts" in out
        and "w1" in out
        and "low confidence" in out
    )


def test_render_full_with_synthesis():
    report = _basic_report(
        compiled_synthesis="cs",
        opportunity_analysis="oa",
        report_summary="rs",
        stage_timings=[{"stage": "fetch", "elapsed_s": 1.0}, {"stage": "score", "elapsed_s": 0.5}],
    )
    out = formatter.render_full(report)
    assert "cs" in out and "oa" in out and "rs" in out
    assert "Timing" in out


def test_render_full_no_synthesis():
    out = formatter.render_full(_basic_report())
    assert "LLM synthesis unavailable" in out


def test_render_timing_footer_empty():
    assert formatter._render_timing_footer([]) == ""


def test_render_timing_footer_skips_invalid():
    out = formatter._render_timing_footer(["not a dict"])
    assert out == ""


def test_to_bullets():
    assert formatter._to_bullets("a; b; c").count("- ") == 3
    assert formatter._to_bullets("") == ""


def test_highlights_table_empty():
    assert "(no highlights)" in formatter._highlights_table([])


def test_highlights_table_with_data():
    out = formatter._highlights_table(["Mean overall: 0.5 — note", "Mean overall: 0.6"])
    assert "| Model |" in out


def test_resolve_summary_uses_stored():
    assert formatter.resolve_report_summary({"report_summary": "stored"}) == "stored"


def test_resolve_summary_filters_placeholder():
    out = formatter.resolve_report_summary(
        {"report_summary": "(LLM synthesis unavailable note)", "topic": "t", "platform": "p"}
    )
    assert "covers t" in out


def test_build_fallback_minimum():
    assert formatter.build_fallback_report_summary({}) is None


def test_build_fallback_topic_only():
    out = formatter.build_fallback_report_summary({"topic": "ai"})
    assert "ai" in out


def test_build_fallback_full():
    report = {
        "topic": "ai",
        "platform": "youtube",
        "source_validation_summary": {
            "validated": 3,
            "partially": 1,
            "unverified": 1,
            "low_trust": 0,
        },
        "compiled_synthesis": "Some synthesis text.",
        "opportunity_analysis": "Op text.",
        "stats_summary": {"highlights": ["Mean: 0.5"], "low_confidence": False},
        "chart_takeaways": ["takeaway one"],
        "platform_engagement_summary": "engagement",
        "evidence_summary": "evidence",
        "warnings": ["warn"],
    }
    out = formatter.build_fallback_report_summary(report)
    assert "ai" in out and "validated" in out


def test_build_fallback_low_confidence_only():
    out = formatter.build_fallback_report_summary(
        {"topic": "x", "stats_summary": {"low_confidence": True}}
    )
    assert "low confidence" in out


def test_usable_summary_filters_placeholder():
    assert formatter._usable_summary_text("LLM synthesis unavailable") == ""
    assert formatter._usable_summary_text("real text") == "real text"
    assert formatter._usable_summary_text(None) == ""
