"""Timing footer rendering and progress-log gating."""

from __future__ import annotations

from social_research_probe.synthesize.formatter import _render_timing_footer, render_full
from social_research_probe.utils import progress


def _packet_with_timings(timings):
    return {
        "topic": "x",
        "platform": "youtube",
        "purpose_set": [],
        "items_top_n": [],
        "source_validation_summary": {
            "validated": 0,
            "partially": 0,
            "unverified": 0,
            "low_trust": 0,
            "primary": 0,
            "secondary": 0,
            "commentary": 0,
            "notes": "",
        },
        "platform_signals_summary": "",
        "evidence_summary": "",
        "stats_summary": {"models_run": [], "highlights": [], "low_confidence": False},
        "chart_captions": [],
        "chart_takeaways": [],
        "warnings": [],
        "stage_timings": timings,
    }


def test_render_timing_footer_with_entries():
    line = _render_timing_footer(
        [
            {"stage": "fetch", "elapsed_s": 1.5, "status": "ok"},
            {"stage": "enrich", "elapsed_s": 8.3, "status": "ok"},
        ]
    )
    assert "fetch 1.5s" in line
    assert "enrich 8.3s" in line
    assert "total 9.8s" in line


def test_render_timing_footer_skips_non_dict_entries():
    """Defensive: a non-dict entry is skipped rather than raising."""
    line = _render_timing_footer(["bogus", {"stage": "ok", "elapsed_s": 0.1}])
    assert "ok 0.1s" in line


def test_render_timing_footer_empty_when_only_invalid_entries():
    assert _render_timing_footer(["bogus", 42]) == ""


def test_render_full_appends_timing_footer():
    body = render_full(_packet_with_timings([{"stage": "fetch", "elapsed_s": 0.1, "status": "ok"}]))
    assert "_Timing:" in body


def test_render_full_no_footer_when_timings_empty():
    body = render_full(_packet_with_timings([]))
    assert "_Timing:" not in body


def test_progress_log_emits_when_env_enabled(monkeypatch, capsys):
    monkeypatch.setenv("SRP_LOGS", "1")
    progress.log("hello srp")
    captured = capsys.readouterr()
    assert "hello srp" in captured.err


def test_progress_log_silent_when_disabled(monkeypatch, capsys):
    """With SRP_LOGS unset and config.progress_log=False, log() emits nothing.

    Explicitly stubbing load_active_config makes the test robust under
    parallel test runners (pytest-xdist), where the default resolution
    could otherwise pick up a real user ~/.social-research-probe/config.toml
    that has progress_log enabled.
    """
    monkeypatch.delenv("SRP_LOGS", raising=False)
    monkeypatch.setattr(
        "social_research_probe.config.load_active_config",
        lambda: type("C", (), {"progress_log": False})(),
    )
    progress.log("should not appear")
    captured = capsys.readouterr()
    assert captured.err == ""


def test_progress_enabled_swallows_config_load_errors(monkeypatch):
    """If config loading fails, _enabled() must return False rather than raise."""

    def _broken():
        raise RuntimeError("config broken")

    monkeypatch.setattr("social_research_probe.config.load_active_config", _broken)
    monkeypatch.delenv("SRP_LOGS", raising=False)
    assert progress._enabled() is False
