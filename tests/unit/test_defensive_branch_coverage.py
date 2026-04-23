"""Defensive-branch coverage across LLM runners, enrichment, viz, and reporting.

Grab-bag of tests that exercise fallback / error / empty-input branches
that aren't naturally covered by happy-path tests elsewhere.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import patch

import pytest

import social_research_probe.llm.gemini_cli as gc
from social_research_probe.cli import _flag, _write_final_report
from social_research_probe.config import Config
from social_research_probe.errors import AdapterError
from social_research_probe.llm.base import LLMRunner
from social_research_probe.llm.runners.gemini import GeminiRunner
from social_research_probe.pipeline import enrichment
from social_research_probe.pipeline.charts import (
    _chart_takeaways,
    _interpret_distribution,
    _interpret_outlier,
    _interpret_strongest_correlation,
)
from social_research_probe.pipeline.orchestrator import _divergence_warnings

# ---------------------------------------------------------------- llm/base.py


class _NoOpRunner(LLMRunner):
    name = "noop"

    def health_check(self):
        return True

    def run(self, prompt, *, schema=None):
        return {}


@pytest.mark.asyncio
async def test_default_summarize_media_returns_none():
    assert await _NoOpRunner().summarize_media("https://x") is None


# ---------------------------------------------------------------- gemini_cli.py


@pytest.fixture(autouse=True)
def _reset_cache():
    gc._AVAILABILITY_CACHE = None
    yield
    gc._AVAILABILITY_CACHE = None


def test_unwrap_envelope_rejects_non_dict():
    with pytest.raises(ValueError):
        gc._unwrap_envelope("[1,2,3]")


def test_extract_answer_returns_empty_when_response_not_string():
    assert gc._extract_answer({"response": 42}) == ""


def test_extract_citations_handles_nested_dict_form():
    envelope = {"grounding": {"citations": [{"title": "T", "url": "u", "snippet": "s"}]}}
    out = gc._extract_citations(envelope)
    assert out[0]["url"] == "u"


def test_extract_citations_skips_non_dict_entries():
    envelope = {"grounding": ["bogus", {"title": "T", "url": "u", "snippet": ""}]}
    out = gc._extract_citations(envelope)
    assert len(out) == 1
    assert out[0]["title"] == "T"


# ---------------------------------------------------------------- runners/gemini.py


@pytest.mark.asyncio
async def test_gemini_runner_summarize_media_returns_none_when_unhealthy():
    runner = GeminiRunner()
    with patch.object(runner, "health_check", return_value=False):
        assert await runner.summarize_media("https://y/1") is None


@pytest.mark.asyncio
async def test_gemini_runner_summarize_media_returns_none_on_subprocess_error():
    runner = GeminiRunner()
    with (
        patch.object(runner, "health_check", return_value=True),
        patch(
            "social_research_probe.llm.runners.gemini.sp_run",
            side_effect=AdapterError("boom"),
        ),
    ):
        assert await runner.summarize_media("https://y/1") is None


@pytest.mark.asyncio
async def test_gemini_runner_summarize_media_returns_none_on_bad_envelope():
    class _Fake:
        stdout = "[]"  # not a dict

    runner = GeminiRunner()
    with (
        patch.object(runner, "health_check", return_value=True),
        patch("social_research_probe.llm.runners.gemini.sp_run", return_value=_Fake()),
    ):
        assert await runner.summarize_media("https://y/1") is None


@pytest.mark.asyncio
async def test_gemini_runner_summarize_media_returns_none_when_response_not_string():
    class _Fake:
        stdout = json.dumps({"response": 42})

    runner = GeminiRunner()
    with (
        patch.object(runner, "health_check", return_value=True),
        patch("social_research_probe.llm.runners.gemini.sp_run", return_value=_Fake()),
    ):
        assert await runner.summarize_media("https://y/1") is None


@pytest.mark.asyncio
async def test_gemini_runner_summarize_media_happy_path():
    class _Fake:
        stdout = json.dumps({"response": "Summary text  "})

    runner = GeminiRunner()
    with (
        patch.object(runner, "health_check", return_value=True),
        patch("social_research_probe.llm.runners.gemini.sp_run", return_value=_Fake()),
    ):
        out = await runner.summarize_media("https://y/1")
    assert out == "Summary text"


@pytest.mark.asyncio
async def test_gemini_runner_summarize_media_returns_none_when_response_blank():
    class _Fake:
        stdout = json.dumps({"response": "   "})

    runner = GeminiRunner()
    with (
        patch.object(runner, "health_check", return_value=True),
        patch("social_research_probe.llm.runners.gemini.sp_run", return_value=_Fake()),
    ):
        assert await runner.summarize_media("https://y/1") is None


# ---------------------------------------------------------------- charts.py


def test_interpret_distribution_empty_returns_empty_string():
    assert _interpret_distribution("x", []) == ""


def test_interpret_strongest_correlation_zero_variance_returns_undefined():
    items = [
        {
            "scores": {"trust": 0.5, "trend": 0.5, "opportunity": 0.5, "overall": 0.5},
            "features": {
                "view_velocity": 1.0,
                "engagement_ratio": 1.0,
                "age_days": 1.0,
                "subscriber_count": 0.0,
            },
        }
        for _ in range(3)
    ]
    line = _interpret_strongest_correlation(items)
    assert "undefined" in line


def test_interpret_outlier_returns_none_for_few_items():
    assert _interpret_outlier([], []) is None


def test_chart_takeaways_includes_outlier_when_present():
    items = [
        {
            "title": f"v{i}",
            "channel": "c",
            "url": "u",
            "scores": {"trust": 0.5, "trend": 0.5, "opportunity": 0.5, "overall": 0.5},
            "features": {
                "view_velocity": 1.0,
                "engagement_ratio": 0.05,
                "age_days": 5.0,
                "subscriber_count": 100.0,
            },
        }
        for i in range(5)
    ]
    items.append(
        {
            "title": "anomaly spike",
            "channel": "c",
            "url": "u",
            "scores": {"trust": 0.5, "trend": 0.5, "opportunity": 0.5, "overall": 0.99},
            "features": {
                "view_velocity": 5.0,
                "engagement_ratio": 0.5,
                "age_days": 1.0,
                "subscriber_count": 5000.0,
            },
        }
    )
    out = _chart_takeaways(items)
    assert any("Outlier" in t for t in out)


# ---------------------------------------------------------------- enrichment.py


def test_first_media_url_runner_swallows_get_runner_exception():
    class _Cfg:
        llm_runner = "gemini"

    with patch(
        "social_research_probe.llm.registry.get_runner",
        side_effect=RuntimeError("boom"),
    ):
        assert enrichment._first_media_url_runner(_Cfg()) is None


@pytest.mark.asyncio
async def test_url_based_summary_swallows_runner_exception(monkeypatch):
    class _Cfg:
        def feature_enabled(self, name):
            return True

    class _Runner:
        async def summarize_media(self, url, *, word_limit):
            raise RuntimeError("boom")

    monkeypatch.setattr(
        "social_research_probe.pipeline.enrichment.load_active_config", lambda: _Cfg()
    )
    monkeypatch.setattr(
        "social_research_probe.pipeline.enrichment._first_media_url_runner",
        lambda _cfg=None: _Runner(),
    )
    out = await enrichment._url_based_summary("https://y/1", word_limit=100)
    assert out is None


@pytest.mark.asyncio
async def test_url_based_summary_returns_falsy_without_caching_when_runner_empty(monkeypatch):
    """Runner returns None: reach line 74 with falsy summary so the cache-write branch is skipped."""

    class _Cfg:
        def feature_enabled(self, name):
            return True

    class _Runner:
        async def summarize_media(self, url, *, word_limit):
            return None

    monkeypatch.setattr(
        "social_research_probe.pipeline.enrichment.load_active_config", lambda: _Cfg()
    )
    monkeypatch.setattr(
        "social_research_probe.pipeline.enrichment._first_media_url_runner",
        lambda _cfg=None: _Runner(),
    )
    out = await enrichment._url_based_summary(
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ", word_limit=100
    )
    assert out is None


@pytest.mark.asyncio
async def test_reconcile_summaries_passes_through_to_multi_llm(monkeypatch):
    captured = {}

    async def _fake(prompt, task=""):
        captured["prompt"] = prompt
        captured["task"] = task
        return "merged"

    monkeypatch.setattr("social_research_probe.pipeline.enrichment.multi_llm_prompt", _fake)
    out = await enrichment._reconcile_summaries("title", "channel", "ts", "us", 100)
    assert out == "merged"
    assert "title" in captured["prompt"]
    assert "channel" in captured["prompt"]


@pytest.mark.asyncio
async def test_enrich_one_short_circuits_when_disabled(monkeypatch):
    from typing import ClassVar

    class _Cfg:
        tunables: ClassVar[dict] = {}

        def feature_enabled(self, name):
            return name != "enrichment_enabled"

    monkeypatch.setattr(
        "social_research_probe.pipeline.enrichment.load_active_config", lambda: _Cfg()
    )

    item = {"title": "x", "url": "https://y/1"}
    sem = asyncio.Semaphore(1)

    def _never(*_a, **_kw):
        raise AssertionError("must not be called when enrichment disabled")

    await enrichment._enrich_one(item, _never, _never, sem)
    assert "summary" not in item


@pytest.mark.asyncio
async def test_merge_or_pick_uses_reconcile_truthy_branch(monkeypatch):
    """When the reconciler returns a truthy string, it short-circuits the divergence return."""

    class _Cfg:
        def feature_enabled(self, name):
            return True

    monkeypatch.setattr(
        "social_research_probe.pipeline.enrichment.load_active_config", lambda: _Cfg()
    )

    async def _ok(*_a, **_kw):
        return "merged-result"

    monkeypatch.setattr("social_research_probe.pipeline.enrichment._reconcile_summaries", _ok)
    item: dict = {"title": "v"}
    out = await enrichment._merge_or_pick(item, "alpha", "beta", "", 100, 0.4)
    assert out == "merged-result"


# ---------------------------------------------------------------- orchestrator.py


def test_divergence_warnings_emits_when_above_threshold(tmp_path):
    cfg = Config.load(tmp_path)
    top_n = [
        {"title": "Bad video", "summary_divergence": 0.9},
        {"title": None, "summary_divergence": 0.95},
    ]
    out = _divergence_warnings(top_n, cfg)
    assert any("Bad video" in line for line in out)
    assert any("untitled" in line for line in out)


# ---------------------------------------------------------------- cli/__init__.py


def test_flag_returns_default_when_method_missing():
    class _Empty:
        pass

    assert _flag(_Empty(), "anything", default=True) is True


def test_flag_returns_default_when_method_raises():
    class _Bad:
        def feature_enabled(self, name):
            raise RuntimeError("boom")

    assert _flag(_Bad(), "x", default=False) is False


def test_write_final_report_falls_back_to_markdown_on_html_exception(tmp_path, monkeypatch):
    cfg = Config.load(tmp_path)
    monkeypatch.setattr(
        "social_research_probe.render.html.write_html_report",
        lambda packet, data_dir: (_ for _ in ()).throw(RuntimeError("html broken")),
    )
    path = _write_final_report(
        {"topic": "x", "platform": "youtube"}, tmp_path, cfg, allow_html=True
    )
    assert path.endswith(".md")
    assert Path(path).exists()


@pytest.mark.asyncio
async def test_fetch_transcript_skipped_when_flag_off(monkeypatch):
    class _Cfg:
        def feature_enabled(self, name):
            return False

    monkeypatch.setattr(
        "social_research_probe.pipeline.enrichment.load_active_config", lambda: _Cfg()
    )
    sem = asyncio.Semaphore(1)

    def _never(*_a, **_kw):
        raise AssertionError("transcript_fetch should be skipped")

    out = await enrichment._fetch_transcript_with_fallback(
        {"url": "https://y/1"}, _never, _never, sem
    )
    assert out == ""


@pytest.mark.asyncio
async def test_merge_or_pick_falls_through_when_reconcile_returns_falsy(monkeypatch):
    """Reconciler returning empty/None means we fall back to the text summary."""

    class _Cfg:
        def feature_enabled(self, name):
            return True

    async def _empty(*_a, **_kw):
        return None

    monkeypatch.setattr(
        "social_research_probe.pipeline.enrichment.load_active_config", lambda: _Cfg()
    )
    monkeypatch.setattr("social_research_probe.pipeline.enrichment._reconcile_summaries", _empty)
    item: dict = {"title": "v"}
    out = await enrichment._merge_or_pick(item, "text-only", "url-only", "", 100, 0.4)
    assert out == "text-only"


def test_divergence_warnings_skips_below_threshold_and_none(tmp_path):
    """Covers continue branches: divergence None and divergence ≤ threshold."""
    cfg = Config.load(tmp_path)
    top_n = [
        {"title": "no divergence"},  # missing → continue
        {"title": "below threshold", "summary_divergence": 0.1},  # ≤ threshold → continue
        {"title": "above", "summary_divergence": 0.95},
    ]
    out = _divergence_warnings(top_n, cfg)
    assert len(out) == 1
    assert "above" in out[0]


def test_extract_citations_continues_when_nested_value_is_not_list():
    """Covers gemini_cli branch where the nested citations value is not a list."""
    envelope = {
        "grounding": {"citations": {"oops": "dict-not-list"}},
        "citations": [{"title": "T", "url": "u", "snippet": "s"}],
    }
    out = gc._extract_citations(envelope)
    assert out and out[0]["title"] == "T"


def test_interpret_outlier_returns_none_when_stdev_zero():
    items = [
        {
            "title": f"v{i}",
            "scores": {"overall": 0.5},
            "channel": "c",
            "url": "u",
            "features": {
                "view_velocity": 1.0,
                "engagement_ratio": 0.05,
                "age_days": 5.0,
                "subscriber_count": 100.0,
            },
        }
        for i in range(5)
    ]
    overall = [d["scores"]["overall"] for d in items]
    assert _interpret_outlier(items, overall) is None


def _setup_purposes(tmp_path):
    from tests.unit.test_pipeline import _write_purposes

    _write_purposes(
        tmp_path,
        {"latest-news": {"method": "Track latest", "evidence_priorities": []}},
    )


def test_run_research_skip_reason_when_no_backends(monkeypatch, tmp_path):
    """Covers orchestrator.py:181 (skip_reason assignment when not backends)."""
    import asyncio as _asyncio

    from social_research_probe.commands.parse import parse
    from social_research_probe.pipeline import run_research

    monkeypatch.setenv("SRP_TEST_USE_FAKE_YOUTUBE", "1")
    _setup_purposes(tmp_path)
    monkeypatch.setattr(
        "social_research_probe.pipeline.orchestrator._available_backends",
        lambda d, cfg=None: [],
    )
    raw = 'run-research platform:youtube "ai"->latest-news'
    packet = _asyncio.run(run_research(parse(raw), tmp_path))
    assert "warnings" in packet


def test_run_research_caps_top_n_and_backends_in_fast_mode(monkeypatch, tmp_path):
    """Fast mode forces enrich_top_n<=3 and limits corroboration to one backend."""
    import asyncio as _asyncio

    from social_research_probe.commands.parse import parse
    from social_research_probe.pipeline import run_research

    monkeypatch.setenv("SRP_TEST_USE_FAKE_YOUTUBE", "1")
    monkeypatch.setenv("SRP_FAST_MODE", "1")
    _setup_purposes(tmp_path)

    monkeypatch.setattr(
        "social_research_probe.pipeline.orchestrator._available_backends",
        lambda d, cfg=None: ["exa", "brave", "tavily"],
    )

    captured = {"backends": None, "top_n_len": None}

    async def _fake_corroborate(top_n, backends):
        captured["backends"] = list(backends)
        captured["top_n_len"] = len(top_n)
        return [{"aggregate_verdict": "supported"} for _ in top_n]

    monkeypatch.setattr(
        "social_research_probe.pipeline.corroboration._corroborate_top_n", _fake_corroborate
    )
    raw = 'run-research platform:youtube "ai"->latest-news'
    _asyncio.run(run_research(parse(raw), tmp_path))

    assert captured["backends"] == ["exa"]
    assert captured["top_n_len"] <= 3


def test_run_research_skips_non_string_verdict(monkeypatch, tmp_path):
    """Covers orchestrator.py:172->170 branch (verdict is not a str)."""
    import asyncio as _asyncio

    from social_research_probe.commands.parse import parse
    from social_research_probe.pipeline import run_research

    async def _fake_corroborate(top_n, backends):
        return [{"aggregate_verdict": 999} for _ in top_n]

    monkeypatch.setenv("SRP_TEST_USE_FAKE_YOUTUBE", "1")
    _setup_purposes(tmp_path)
    monkeypatch.setattr(
        "social_research_probe.pipeline.orchestrator._available_backends",
        lambda d, cfg=None: ["exa"],
    )
    monkeypatch.setattr(
        "social_research_probe.pipeline.corroboration._corroborate_top_n", _fake_corroborate
    )
    raw = 'run-research platform:youtube "ai"->latest-news'
    packet = _asyncio.run(run_research(parse(raw), tmp_path))
    for item in packet.get("items_top_n", []):
        assert "corroboration_verdict" not in item


def test_handle_research_skips_synthesis_when_flag_off(monkeypatch, tmp_path):
    """Covers the if cfg.feature_enabled('synthesis_enabled') False branch."""
    from unittest.mock import AsyncMock

    from social_research_probe.cli import main

    monkeypatch.setattr(
        "social_research_probe.pipeline.run_research",
        AsyncMock(return_value={"topic": "t", "platform": "youtube", "items_top_n": []}),
    )

    called: list = []
    monkeypatch.setattr(
        "social_research_probe.cli._attach_synthesis", lambda pkt: called.append(pkt)
    )

    cfg = Config.load(tmp_path)
    cfg.raw["features"]["synthesis_enabled"] = False
    monkeypatch.setattr("social_research_probe.cli.load_active_config", lambda: cfg)

    rc = main(["--data-dir", str(tmp_path), "research", "youtube", "AI", "latest-news"])
    assert rc == 0
    assert called == []
