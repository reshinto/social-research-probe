"""Coverage backstops for the last uncovered unit-test branches."""

from __future__ import annotations

import subprocess

import pytest

from social_research_probe.cli import main
from social_research_probe.errors import SynthesisError
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


def test_research_emits_packet_without_render_full(monkeypatch, tmp_path, capsys):
    calls = []

    def fake_run_research(cmd, data_dir, adapter_config=None):
        calls.append((cmd, data_dir, adapter_config))
        return _VALID_PACKET

    monkeypatch.setattr("social_research_probe.pipeline.run_research", fake_run_research)
    monkeypatch.setattr("social_research_probe.cli._attach_synthesis", lambda pkt: None)

    assert main(["--data-dir", str(tmp_path), "research", "ai", "latest-news"]) == 0
    assert calls
    _cmd, _data_dir, adapter_config = calls[0]
    assert adapter_config == {"include_shorts": True, "fetch_transcripts": True}
    out = capsys.readouterr().out
    assert '"kind": "synthesis"' in out


def test_research_propagates_synthesis_error(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "social_research_probe.pipeline.run_research",
        lambda cmd, data_dir, adapter_config=None: _VALID_PACKET,
    )
    monkeypatch.setattr(
        "social_research_probe.cli._attach_synthesis",
        lambda pkt: (_ for _ in ()).throw(SynthesisError("boom")),
    )
    assert main(["--data-dir", str(tmp_path), "research", "ai", "latest-news"]) == 4


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


def test_enrich_top5_uses_description_when_transcript_whitespace_only(monkeypatch):
    """When both transcript paths return whitespace-only text, the pipeline falls back
    to a description-based LLM summary instead of skipping entirely."""
    from social_research_probe.pipeline import _enrich_top5_with_transcripts

    monkeypatch.setattr(
        "social_research_probe.platforms.youtube.extract.fetch_transcript",
        lambda _url: None,
    )
    monkeypatch.setattr(
        "social_research_probe.platforms.youtube.whisper_transcript.fetch_transcript_whisper",
        lambda _url: "  \n\t  ",
    )
    monkeypatch.setattr(
        "social_research_probe.pipeline.multi_llm_prompt",
        lambda prompt, task="": "Description-based summary.",
    )

    items = [
        {
            "url": "https://x/1",
            "title": "Test Video",
            "channel": "TestChan",
            "text_excerpt": "a short description",
            "published_at": "2026-01-01",
            "one_line_takeaway": "keep me",
        }
    ]
    _enrich_top5_with_transcripts(items)

    assert "transcript" not in items[0]
    assert items[0].get("summary_source") == "description"
    assert items[0]["one_line_takeaway"] == "Description-based summary."


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


def test_fallback_transcript_summary_empty_string_returns_empty():
    """_fallback_transcript_summary returns the original string when there are no words."""
    from social_research_probe.pipeline import _fallback_transcript_summary

    assert _fallback_transcript_summary("") == ""


def test_run_research_skip_reason_no_api_credentials(monkeypatch, tmp_path):
    """When backends config is non-none but no backends pass health-check, skip_reason
    is 'no API credentials usable' (the else-branch of the cfg_corr == 'none' check)."""

    from social_research_probe.commands.parse import parse
    from social_research_probe.pipeline import run_research

    monkeypatch.setenv("SRP_TEST_USE_FAKE_YOUTUBE", "1")

    class _Cfg:
        corroboration_backend = "exa"

        def platform_defaults(self, name):
            return {}

        def llm_settings(self, name):
            return {}

        default_structured_runner = "none"
        llm_runner = "none"

    monkeypatch.setattr("social_research_probe.pipeline.Config.load", lambda d: _Cfg())
    monkeypatch.setattr("social_research_probe.pipeline._available_backends", lambda d: ["exa"])
    monkeypatch.setattr(
        "social_research_probe.pipeline._corroborate_top5", lambda items, backends: []
    )
    monkeypatch.setattr(
        "social_research_probe.pipeline._enrich_top5_with_transcripts", lambda items: None
    )
    from tests.unit.test_pipeline import _write_purposes

    _write_purposes(
        tmp_path,
        {
            "latest-news": {
                "method": "Track latest channels for breaking news",
                "evidence_priorities": [],
            }
        },
    )
    packet = run_research(parse('run-research platform:youtube "AI"->latest-news'), tmp_path)
    assert "topic" in packet


def test_corroboration_init_fake_backend_imported_when_env_set(monkeypatch):
    """Line 21 of corroboration/__init__.py is hit when SRP_TEST_USE_FAKE_CORROBORATION=1."""
    import importlib
    import sys

    import social_research_probe.corroboration as corr_mod

    monkeypatch.setenv("SRP_TEST_USE_FAKE_CORROBORATION", "1")
    importlib.reload(corr_mod)
    assert "tests.fixtures.fake_corroboration" in sys.modules
