"""Tests for Phase 3 methodology markdown builder."""

from __future__ import annotations

from pathlib import Path

from social_research_probe.technologies.report_render.export.methodology_md import (
    build_methodology,
    write_methodology,
)


def _minimal_report(**kwargs) -> dict:
    return {"topic": "AI safety", "platform": "youtube", **kwargs}


def _minimal_config(**kwargs) -> dict:
    return {
        "max_items": 20,
        "enrich_top_n": 5,
        "recency_days": 90,
        **kwargs,
    }


def test_build_includes_topic():
    out = build_methodology(_minimal_report(), _minimal_config())
    assert "AI safety" in out


def test_build_includes_platform():
    out = build_methodology(_minimal_report(), _minimal_config())
    assert "youtube" in out


def test_build_includes_purpose_set():
    report = _minimal_report(purpose_set=["competitive analysis", "trend spotting"])
    out = build_methodology(report, _minimal_config())
    assert "competitive analysis" in out
    assert "trend spotting" in out


def test_build_includes_config_values():
    out = build_methodology(_minimal_report(), _minimal_config())
    assert "max_items" in out
    assert "enrich_top_n" in out
    assert "recency_days" in out


def test_build_includes_technology_statuses():
    config = _minimal_config(technologies={"youtube_api": True, "whisper": False})
    out = build_methodology(_minimal_report(), config)
    assert "youtube_api" in out
    assert "enabled" in out
    assert "disabled" in out


def test_build_technologies_unavailable_shows_fallback():
    out = build_methodology(_minimal_report(), _minimal_config())
    assert "Not available in platform-level export context" in out


def test_build_includes_evidence_tier_distribution():
    items = [
        {"evidence_tier": "metadata_transcript"},
        {"evidence_tier": "metadata_transcript"},
        {"evidence_tier": "metadata_only"},
    ]
    report = _minimal_report(items_top_n=items)
    out = build_methodology(report, _minimal_config())
    assert "metadata_transcript" in out
    assert "metadata_only" in out
    assert "2" in out


def test_build_includes_transcript_comments_coverage():
    items = [
        {"transcript_status": "available", "comments_status": "available"},
        {"transcript_status": "unavailable", "comments_status": "disabled"},
    ]
    report = _minimal_report(items_top_n=items)
    out = build_methodology(report, _minimal_config())
    assert "transcript_status" in out
    assert "comments_status" in out
    assert "available" in out


def test_build_includes_stage_timings():
    timings = [
        {"stage": "fetch", "elapsed_s": 1.2, "status": "ok"},
        {"stage": "score", "elapsed_s": 0.3, "status": "ok"},
    ]
    report = _minimal_report(stage_timings=timings)
    out = build_methodology(report, _minimal_config())
    assert "fetch" in out
    assert "score" in out
    assert "Stage" in out


def test_build_includes_warnings():
    report = _minimal_report(warnings=["low trust items present", "LLM timeout"])
    out = build_methodology(report, _minimal_config())
    assert "low trust items present" in out
    assert "LLM timeout" in out


def test_build_empty_report_no_crash():
    out = build_methodology({}, {})
    assert "# Methodology" in out
    assert "## Research Query" in out
    assert "## Warnings" in out


def test_write_creates_file(tmp_path: Path):
    content = build_methodology(_minimal_report(), _minimal_config())
    out = tmp_path / "methodology.md"
    result = write_methodology(content, out)
    assert out.exists()
    assert result == out
    assert "# Methodology" in out.read_text(encoding="utf-8")


def test_build_unicode_preserved():
    report = _minimal_report(topic="人工知能の安全性", warnings=["警告メッセージ"])
    out = build_methodology(report, _minimal_config())
    assert "人工知能の安全性" in out
    assert "警告メッセージ" in out


def test_build_includes_comments_config():
    config = _minimal_config(comments={"enabled": True, "max_videos": 5, "order": "relevance"})
    out = build_methodology(_minimal_report(), config)
    assert "comments" in out
    assert "max_videos" in out


def test_build_includes_scoring_weights():
    config = _minimal_config(scoring={"weights": {"trust": 0.5, "trend": 0.3, "opportunity": 0.2}})
    out = build_methodology(_minimal_report(), config)
    assert "scoring weights" in out
    assert "trust" in out


def test_build_scoring_weights_unavailable_shows_fallback():
    out = build_methodology(_minimal_report(), _minimal_config())
    assert "Not available in platform-level export context" in out


def test_build_stage_timings_skips_non_dict_entries():
    timings = [{"stage": "fetch", "elapsed_s": 1.0, "status": "ok"}, "bad-entry", None]
    report = _minimal_report(stage_timings=timings)
    out = build_methodology(report, _minimal_config())
    assert "fetch" in out
    assert "Stage Timings" in out
