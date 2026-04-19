"""Coverage backstops for the last uncovered unit-test branches."""

from __future__ import annotations

import subprocess

import pytest

from social_research_probe.cli import main
from social_research_probe.llm.ensemble import _run_provider
from social_research_probe.pipeline import _fetch_best_transcript
from social_research_probe.synthesize.formatter import (
    _explain_bayesian,
    _explain_descriptive,
    _explain_huber,
    _explain_polynomial,
    _explain_regression,
)

_VALID_PACKET = {
    "topic": "ai",
    "platform": "youtube",
    "purpose_set": ["latest-news"],
    "items_top5": [],
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
    "platform_signals_summary": "0 items",
    "evidence_summary": "0 items",
    "stats_summary": {"models_run": [], "highlights": [], "low_confidence": False},
    "chart_captions": [],
    "warnings": [],
}


def test_research_skill_mode_skips_render_full(monkeypatch, tmp_path):
    calls = []

    def fake_run_research(cmd, data_dir, mode, adapter_config=None, pre_emit_hook=None):
        calls.append((cmd, data_dir, mode, adapter_config))
        return _VALID_PACKET

    def fail_render_full(*args, **kwargs):
        raise AssertionError("render_full should not be called in skill mode")

    monkeypatch.setattr("social_research_probe.pipeline.run_research", fake_run_research)
    monkeypatch.setattr("social_research_probe.synthesize.formatter.render_full", fail_render_full)

    assert (
        main(["--data-dir", str(tmp_path), "research", "--mode", "skill", "ai", "latest-news"]) == 0
    )
    assert calls
    _cmd, _data_dir, mode, adapter_config = calls[0]
    assert mode == "skill"
    assert adapter_config == {"include_shorts": True, "fetch_transcripts": True}


@pytest.mark.parametrize(
    ("provider", "expected_command"),
    [
        ("gemini", ["gemini", "-p", "hello"]),
        ("codex", ["codex", "exec", "hello"]),
    ],
)
def test_run_provider_uses_expected_command(monkeypatch, provider, expected_command):
    calls = []

    class Result:
        stdout = "  answer  "

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return Result()

    monkeypatch.setattr(subprocess, "run", fake_run)

    assert _run_provider(provider, "hello") == "answer"
    assert len(calls) == 1
    cmd, kwargs = calls[0]
    assert cmd == expected_command
    assert kwargs["stdin"] == subprocess.DEVNULL
    assert kwargs["capture_output"] is True
    assert kwargs["text"] is True


def test_fetch_best_transcript_returns_none_when_fallback_raises():
    def fallback(_url: str) -> str | None:
        raise RuntimeError("boom")

    assert _fetch_best_transcript("https://example.com", lambda _url: None, fallback) is None


def test_fetch_best_transcript_returns_primary_text_when_available():
    assert (
        _fetch_best_transcript("https://x", lambda _url: "hello world", lambda _url: None)
        == "hello world"
    )


def test_fetch_best_transcript_swallows_primary_exception_and_tries_fallback():
    def primary(_url: str) -> str | None:
        raise OSError("network down")

    assert (
        _fetch_best_transcript("https://x", primary, lambda _url: "fallback text")
        == "fallback text"
    )


def test_enrich_top5_skips_whitespace_only_fallback_transcript(monkeypatch):
    from social_research_probe.pipeline import _enrich_top5_with_transcripts

    def fail_multi_llm(_prompt: str) -> str | None:
        raise AssertionError("multi_llm_prompt should not run for empty cleaned transcripts")

    monkeypatch.setattr(
        "social_research_probe.platforms.youtube.extract.fetch_transcript",
        lambda _url: None,
    )
    monkeypatch.setattr(
        "social_research_probe.platforms.youtube.whisper_transcript.fetch_transcript_whisper",
        lambda _url: "  \n\t  ",
    )
    monkeypatch.setattr("social_research_probe.pipeline.multi_llm_prompt", fail_multi_llm)

    items = [{"url": "https://x/1", "one_line_takeaway": "keep me"}]
    _enrich_top5_with_transcripts(items)

    assert "transcript" not in items[0]
    assert items[0]["one_line_takeaway"] == "keep me"


def test_explain_descriptive_unknown_numeric_metric_returns_empty():
    assert _explain_descriptive("Descriptive surprise: 0.50") == ""


def test_explain_regression_unknown_numeric_metric_returns_empty():
    assert _explain_regression("Regression surprise: 0.10") == ""


def test_explain_polynomial_unknown_numeric_metric_returns_empty():
    assert _explain_polynomial("Polynomial surprise: 0.10") == ""


def test_explain_huber_unknown_numeric_metric_returns_empty():
    assert _explain_huber("Huber surprise: 0.50") == ""


def test_explain_bayesian_unknown_numeric_metric_returns_empty():
    assert _explain_bayesian("Bayesian coef mystery: 0.20 [0.15, 0.25]", "") == ""
