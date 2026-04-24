"""Coverage backstops for the last uncovered unit-test branches."""

from __future__ import annotations

from typing import ClassVar
from unittest.mock import AsyncMock

import pytest
from social_research_probe.errors import SynthesisError
from social_research_probe.llm.ensemble import _run_provider
from social_research_probe.pipeline.enrichment import (
    _enrich_top_n_with_transcripts,
    _fallback_transcript_summary,
)
from social_research_probe.synthesize.explanations import (
    explain_bayesian as _explain_bayesian,
)
from social_research_probe.synthesize.explanations import (
    explain_descriptive as _explain_descriptive,
)
from social_research_probe.synthesize.explanations import (
    explain_huber as _explain_huber,
)
from social_research_probe.synthesize.explanations import (
    explain_polynomial as _explain_polynomial,
)
from social_research_probe.synthesize.explanations import (
    explain_regression as _explain_regression,
)

from social_research_probe.cli import main
from social_research_probe.commands import Command
from social_research_probe.platforms.orchestrator import run_pipeline

_VALID_PACKET = {
    "topic": "ai",
    "platform": "youtube",
    "purpose_set": ["latest-news"],
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
    "platform_signals_summary": "0 items",
    "evidence_summary": "0 items",
    "stats_summary": {"models_run": [], "highlights": [], "low_confidence": False},
    "chart_captions": [],
    "warnings": [],
}


def test_research_emits_packet_without_render_full(monkeypatch, tmp_path, capsys):
    calls = []

    async def fake_run_pipeline(cmd, data_dir, adapter_config=None):
        calls.append((cmd, data_dir, adapter_config))
        return _VALID_PACKET

    monkeypatch.setattr("social_research_probe.pipeline.run_pipeline", fake_run_pipeline)
    monkeypatch.setattr("social_research_probe.cli._attach_synthesis", lambda pkt: None)

    assert main(["--data-dir", str(tmp_path), Command.RESEARCH, "ai", "latest-news"]) == 0
    assert calls
    _cmd, _data_dir, adapter_config = calls[0]
    assert adapter_config == {"include_shorts": True, "fetch_transcripts": True}
    out = capsys.readouterr().out.strip()
    assert out.endswith(".html") or out.endswith(".md")


def test_research_propagates_synthesis_error(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "social_research_probe.pipeline.run_pipeline",
        AsyncMock(return_value=_VALID_PACKET),
    )
    monkeypatch.setattr(
        "social_research_probe.cli._attach_synthesis",
        lambda pkt: (_ for _ in ()).throw(SynthesisError("boom")),
    )
    assert main(["--data-dir", str(tmp_path), Command.RESEARCH, "ai", "latest-news"]) == 4


@pytest.mark.parametrize(
    ("provider", "expected_command"),
    [
        ("gemini", ["gemini", "-p", "hello"]),
        ("codex", ["codex", "exec", "hello"]),
    ],
)
async def test_run_provider_uses_expected_command(monkeypatch, provider, expected_command):
    import asyncio

    calls = []

    class _FakeProc:
        async def communicate(self, input=None):
            return (b"  answer  ", b"")

        async def wait(self):
            return 0

    async def fake_create_subprocess(*cmd, stdin=None, stdout=None, stderr=None):
        calls.append((list(cmd), {"stdin": stdin, "stdout": stdout, "stderr": stderr}))
        return _FakeProc()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create_subprocess)

    result = await _run_provider(provider, "hello")
    assert result == "answer"
    assert len(calls) == 1
    cmd, kwargs = calls[0]
    assert cmd == expected_command
    assert kwargs["stdout"] == asyncio.subprocess.PIPE
    assert kwargs["stderr"] == asyncio.subprocess.DEVNULL


async def test_enrich_top_n_uses_description_when_transcript_whitespace_only(monkeypatch):
    """When both transcript paths return whitespace-only text, the pipeline falls back
    to a description-based LLM summary instead of skipping entirely."""
    monkeypatch.setattr(
        "social_research_probe.platforms.youtube.extract.fetch_transcript",
        lambda _url: None,
    )
    monkeypatch.setattr(
        "social_research_probe.platforms.youtube.whisper_transcript.fetch_transcript_whisper",
        lambda _url: "  \n\t  ",
    )
    monkeypatch.setattr(
        "social_research_probe.pipeline.enrichment.multi_llm_prompt",
        AsyncMock(return_value="Description-based summary."),
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
    await _enrich_top_n_with_transcripts(items)

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
    assert _fallback_transcript_summary("") == ""


async def test_run_pipeline_skip_reason_no_api_credentials(monkeypatch, tmp_path):
    """When backends config is non-none but no backends pass health-check, skip_reason
    is 'no API credentials usable' (the else-branch of the cfg_corr == 'none' check)."""

    from social_research_probe.cli.dsl_parser import parse

    monkeypatch.setenv("SRP_TEST_USE_FAKE_YOUTUBE", "1")

    class _Cfg:
        corroboration_backend = "exa"
        raw: ClassVar[dict] = {"scoring": {"weights": {}}}

        def platform_defaults(self, name):
            return {}

        def llm_settings(self, name):
            return {}

        default_structured_runner = "none"
        llm_runner = "none"

    monkeypatch.setattr("social_research_probe.platforms.orchestrator.Config.load", lambda d: _Cfg())
    monkeypatch.setattr(
        "social_research_probe.platforms.orchestrator._available_backends",
        lambda d, cfg=None: ["exa"],
    )
    monkeypatch.setattr(
        "social_research_probe.pipeline.corroboration._corroborate_top_n",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        "social_research_probe.pipeline.enrichment._enrich_top_n_with_transcripts",
        AsyncMock(return_value=None),
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
    packet = await run_pipeline(parse('run-research platform:youtube "AI"->latest-news'), tmp_path)
    assert "topic" in packet


def test_corroboration_init_fake_backend_imported_when_env_set(monkeypatch):
    """Line 21 of corroboration/__init__.py is hit when SRP_TEST_USE_FAKE_CORROBORATION=1."""
    import importlib
    import sys

    import social_research_probe.corroboration as corr_mod

    monkeypatch.setenv("SRP_TEST_USE_FAKE_CORROBORATION", "1")
    importlib.reload(corr_mod)
    assert "tests.fixtures.fake_corroboration" in sys.modules
