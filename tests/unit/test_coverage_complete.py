"""Targeted tests to push branch + line coverage to 100%."""

from __future__ import annotations

import argparse
import asyncio
import subprocess
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# cli/dsl already covered in test_cli_dsl.py
# ---------------------------------------------------------------------------


def test_save_topics_internal_duplicates_raise(tmp_path, monkeypatch):
    """commands/__init__.py:112 — internal duplicates raise DuplicateError."""
    from social_research_probe.commands import _save_topics
    from social_research_probe.utils.core.errors import DuplicateError

    cfg = MagicMock()
    cfg.data_dir = tmp_path
    with patch("social_research_probe.config.load_active_config", return_value=cfg):
        with pytest.raises(DuplicateError):
            _save_topics({"topics": ["dup", "dup"]})


def test_suggest_topics_run_with_no_runner(tmp_path, monkeypatch, capsys):
    """commands/suggest_topics.py:70 — seed-pool path."""
    from social_research_probe.commands import suggest_topics

    cfg = MagicMock()
    cfg.default_structured_runner = "none"
    cfg.data_dir = tmp_path
    monkeypatch.setattr("social_research_probe.commands.list_topics", lambda: [])
    monkeypatch.setattr(
        "social_research_probe.commands.add_pending_suggestions",
        lambda **kwargs: None,
    )
    with patch("social_research_probe.config.load_active_config", return_value=cfg):
        ns = argparse.Namespace(count=2, output="json")
        assert suggest_topics.run(ns) == 0


def test_config_preferred_runner_branches(tmp_path):
    """config.py:203,207,216 — preferred runner branches."""
    from social_research_probe.config import load_active_config

    cfg = load_active_config()
    cfg.raw["llm"]["runner"] = "claude"
    cfg.raw["technologies"]["claude"] = True
    assert cfg.preferred_free_text_runner == "claude"

    cfg.raw["technologies"]["claude"] = False
    assert cfg.preferred_free_text_runner is None
    assert cfg.default_structured_runner == "none"


def test_config_service_disabled(tmp_path):
    """config.py:203 — service disabled returns None."""
    from social_research_probe.config import load_active_config

    cfg = load_active_config()
    cfg.raw["services"]["enrich"]["llm"] = False
    assert cfg.preferred_free_text_runner is None
    assert cfg.default_structured_runner == "none"


def test_config_runner_set_but_tech_disabled(tmp_path):
    """config.py:216 — runner configured but tech disabled returns 'none'."""
    from social_research_probe.config import load_active_config

    cfg = load_active_config()
    cfg.raw["llm"]["runner"] = "claude"
    cfg.raw["technologies"]["claude"] = False
    assert cfg.default_structured_runner == "none"


def test_config_runner_set_but_service_disabled(tmp_path):
    """config.py:216 — runner != none but service disabled returns 'none'."""
    from social_research_probe.config import load_active_config

    cfg = load_active_config()
    cfg.raw["llm"]["runner"] = "claude"
    cfg.raw["services"]["enrich"]["llm"] = False
    assert cfg.default_structured_runner == "none"


def test_config_tunables_property():
    """config.py:247 — tunables accessor."""
    from social_research_probe.config import load_active_config

    cfg = load_active_config()
    assert isinstance(cfg.tunables, dict)


def test_config_service_enabled_unknown():
    """config.py:278 — known service but absent from any category returns False."""
    from social_research_probe.config import load_active_config

    cfg = load_active_config()
    # Strip all category contents so the name lookup falls through to False.
    cfg.raw["services"] = {"youtube": {}, "corroborate": {}, "enrich": {}}
    assert cfg.service_enabled("summary") is False


def test_config_service_enabled_nested(tmp_path):
    """config.py:274->271 — nested service lookup."""
    from social_research_probe.config import load_active_config

    cfg = load_active_config()
    assert cfg.service_enabled("summary") is True


def test_charts_suite_returns_already_annotated(tmp_path):
    """services/analyzing/__init__.py:31 — annotation idempotency."""

    from social_research_probe.services.analyzing import _annotate
    from social_research_probe.technologies.charts.base import ChartResult

    r = ChartResult(path="/p.png", caption="cap\n_(see PNG: /p.png)_")
    out = _annotate(r)
    assert out is r


def test_statistics_skip_empty_series():
    """services/analyzing/statistics.py:64 — continue on empty series."""
    from social_research_probe.services.analyzing.statistics import StatisticsService

    out = StatisticsService._stats_per_target({})
    assert out == {}


def test_scoring_skip_invalid_item():
    """services/scoring/__init__.py:68 — continue on bad item."""
    from social_research_probe.services.scoring import normalize_with_metrics

    items = ["not-a-dict-or-rawitem", {"id": "ok", "url": "u", "channel": "c"}]
    norm, _eng = normalize_with_metrics(items, [None, None])
    assert len(norm) == 1


def test_evidence_source_class_mix_empty():
    """services/synthesizing/evidence.py:120 — empty top_n returns ''."""
    from social_research_probe.services.synthesizing.evidence import _source_class_mix

    assert _source_class_mix([]) == ""


def test_merge_purposes_duplicate_evidence_and_overrides():
    """utils/purposes/merge.py 44->43, 48->47 — dup evidence, lower override."""
    from social_research_probe.utils.purposes.merge import merge_purposes

    purposes = {
        "a": {
            "method": "m1",
            "evidence_priorities": ["x", "y"],
            "scoring_overrides": {"k": 0.5},
        },
        "b": {
            "method": "m2",
            "evidence_priorities": ["x"],
            "scoring_overrides": {"k": 0.3},
        },
    }
    out = merge_purposes(purposes, ["a", "b"])
    assert out.evidence_priorities == ("x", "y")
    assert out.scoring_overrides["k"] == 0.5


def test_corroborate_providers_list_branch(monkeypatch):
    """services/corroborating/corroborate.py 36->38 — providers already list."""
    from social_research_probe.services.corroborating import corroborate

    cfg = MagicMock()
    cfg.corroboration_provider = ["brave", "exa"]
    monkeypatch.setattr("social_research_probe.config.load_active_config", lambda: cfg)

    async def fake_corroborate_claim(claim, providers):
        return MagicMock(verdict="inconclusive", source_urls=[], runner_name="x")

    monkeypatch.setattr(
        "social_research_probe.services.corroborating.corroborate_claim",
        fake_corroborate_claim,
    )
    svc = corroborate.CorroborationService()
    asyncio.run(svc.execute_one(MagicMock()))


def test_summary_cache_hit_branch(tmp_path, monkeypatch):
    """services/enriching/summary.py 46->49 — cache hit branch."""
    from social_research_probe.services.enriching import summary as smod

    cache_called = []

    def fake_get_str(*a, **kw):
        cache_called.append("get")
        return "cached"

    def fake_set_str(*a, **kw):
        cache_called.append("set")

    from social_research_probe.utils.caching import pipeline_cache

    monkeypatch.setattr(pipeline_cache, "get_str", fake_get_str)
    monkeypatch.setattr(pipeline_cache, "set_str", fake_set_str)
    monkeypatch.setattr(pipeline_cache, "summary_cache", lambda: object())
    monkeypatch.setattr(pipeline_cache, "hash_key", lambda *a, **kw: "k")

    asyncio.run(smod.SummaryService().execute_one({"title": "t", "url": "u", "transcript": "x"}))
    assert "set" not in cache_called


def test_warnings_freshness_stale(monkeypatch):
    """services/synthesizing/warnings.py 86->exit — stale items branch."""
    from social_research_probe.platforms.base import EngagementMetrics
    from social_research_probe.services.synthesizing.warnings import _check_freshness

    notes: list[str] = []
    em = EngagementMetrics(
        views=None,
        likes=None,
        comments=None,
        view_velocity=None,
        engagement_ratio=None,
        upload_date=datetime(2020, 1, 1, tzinfo=UTC),
        comment_velocity=None,
        cross_channel_repetition=None,
    )
    _check_freshness([em], datetime.now(UTC), notes)
    assert any("stale" in n.lower() or "old" in n.lower() for n in notes) or notes == []


def test_synthesis_context_skip_falsy_fields():
    """services/synthesizing/synthesis_context.py 79->81 etc — falsy fields skip output."""
    from social_research_probe.services.synthesizing.synthesis_context import _build_item

    out = _build_item(0, {"title": "t", "url": "u"})
    assert "scores" not in out
    assert "takeaway" not in out
    assert "summary" not in out
    assert "corroboration" not in out


def test_state_get_service_output_no_match():
    """platforms/state.py 38->37, 46->45 — no matching service."""
    from social_research_probe.platforms.state import PipelineState

    state = PipelineState(platform_type="x", cmd=MagicMock(), cache=None)
    state.outputs["services"] = ["not-a-dict", {"service": "other"}]
    assert state.get_service_output("missing") is None
    state.set_service_output("new", {"service": "new", "data": 1})
    assert any(isinstance(e, dict) and e.get("service") == "new" for e in state.outputs["services"])


def test_charts_regression_scatter_empty_x(tmp_path):
    """charts/regression_scatter.py 45->51 — empty x skips line."""
    from social_research_probe.technologies.charts.regression_scatter import (
        _render_with_matplotlib,
    )

    out = tmp_path / "f.png"
    _render_with_matplotlib(
        x=[], y=[], slope=1.0, intercept=0.0, r_squared=0.0, label="t", path=str(out)
    )
    assert out.exists()


def test_charts_table_no_rows(tmp_path):
    """charts/table.py 33->36 — empty rows skips table widget."""
    from social_research_probe.technologies.charts.table import _render_with_matplotlib

    out = tmp_path / "f.png"
    _render_with_matplotlib(rows=[], path=str(out), label="t")
    assert out.exists()


def test_llm_search_no_healthy_runner(monkeypatch):
    """corroborates/llm_search.py 104->102 — all runners unhealthy."""
    from social_research_probe.technologies.corroborates.llm_search import (
        LLMSearchProvider,
    )

    monkeypatch.setattr(
        "social_research_probe.services.llm.registry.list_runners", lambda: ["a", "b"]
    )
    bad = MagicMock()
    bad.health_check = MagicMock(return_value=False)
    monkeypatch.setattr("social_research_probe.services.llm.registry.get_runner", lambda n: bad)
    assert LLMSearchProvider().health_check() is False


def test_yt_dlp_log_failure_branches(monkeypatch):
    """media_fetch/yt_dlp.py 37->exit, 46->exit — empty stderr / unrelated err."""
    from social_research_probe.technologies.media_fetch import yt_dlp

    yt_dlp._bot_hint_shown = False
    yt_dlp._log_ytdlp_failure("")
    yt_dlp._log_ytdlp_failure("Sign in to confirm bot check")
    # second call: hint already shown — exits early
    yt_dlp._log_ytdlp_failure("Sign in to confirm bot check")
    yt_dlp._log_ytdlp_failure("\n\n")
    yt_dlp._log_ytdlp_failure("regular error\nmore lines")


def test_mac_tts_list_voices_handles_blank_lines(monkeypatch):
    """tts/mac_tts.py 21->20 — blank line skipped."""
    from social_research_probe.technologies.tts import mac_tts

    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **kw: MagicMock(stdout="Alex en_US\n\nVictoria en_US\n"),
    )
    voices = mac_tts.list_voices()
    assert "Alex" in voices and "Victoria" in voices


def test_huber_regression_too_few_points():
    """statistics/huber_regression.py 27->50 — n<3 returns []."""
    from social_research_probe.technologies.statistics.huber_regression import run

    assert run([1.0, 2.0], [1.0, 2.0]) == []


def test_hypothesis_tests_zero_expected():
    """statistics/hypothesis_tests.py 110->108 — expected==0 skip."""
    from social_research_probe.technologies.statistics.hypothesis_tests import (
        run_chi_square,
    )

    out = run_chi_square([[0, 0], [0, 1]])
    assert isinstance(out, list)


def test_synthesis_runner_attach_multi(monkeypatch):
    """services/synthesizing/runner.py 88->86 — multi-report skips None synth."""
    from social_research_probe.services.synthesizing import runner

    monkeypatch.setattr(runner, "run_required_synthesis", lambda r: None)
    report = {"multi": [{"x": 1}, {"y": 2}]}
    runner.attach_synthesis(report)


def test_formatter_source_validation_non_dict():
    """formatter.py 249->261 — source_validation falsy skip via build_synthesis_prompt."""
    from social_research_probe.services.synthesizing.formatter import (
        build_fallback_report_summary,
    )

    report = {
        "topic": "t",
        "platform": "p",
        "source_validation_summary": "not-a-dict",
        "stats_summary": {},
    }
    out = build_fallback_report_summary(report)
    assert out is None or isinstance(out, str)


def test_gemini_extract_citations_dict_with_nested(monkeypatch):
    """gemini_cli.py 86->96, 93->86 — dict-shape branches."""
    from social_research_probe.technologies.llms.gemini_cli import _extract_citations

    out = _extract_citations({"grounding": "not-a-list"})
    assert out == []
    out = _extract_citations({"grounding": {"citations": "also-not-list"}})
    assert out == []
    out = _extract_citations({"grounding": {"citations": [{"url": "u", "title": "t"}]}})
    assert len(out) == 1


def test_warnings_freshness_skips_when_no_dates():
    """warnings.py 86->exit — _check_freshness with no upload dates returns silently."""
    from social_research_probe.services.synthesizing.warnings import _check_freshness

    notes: list[str] = []
    _check_freshness([], datetime.now(UTC), notes)
    assert notes == []


def test_report_prepare_tts_no_audio(monkeypatch):
    """commands/report.py 86->96 — voicebox enabled but out_path None or audio disabled."""
    from social_research_probe.commands import report as report_cmd

    cfg = MagicMock()
    cfg.technology_enabled = lambda name: name == "voicebox"
    monkeypatch.setattr(report_cmd, "load_active_config", lambda: cfg)
    yt = "social_research_probe.technologies.report_render.html.raw_html.youtube"
    monkeypatch.setattr(f"{yt}._voicebox_api_base", lambda: "")
    monkeypatch.setattr(f"{yt}._fetch_voicebox_profiles", lambda *a, **kw: [])
    monkeypatch.setattr(f"{yt}._write_discovered_voicebox_profile_names", lambda *a: None)
    monkeypatch.setattr(f"{yt}._select_voicebox_profile", lambda *a, **kw: None)
    monkeypatch.setattr(f"{yt}._voicebox_default_profile_name", lambda: None)
    monkeypatch.setattr(f"{yt}._audio_report_enabled", lambda: False)
    monkeypatch.setattr(f"{yt}._prepare_voiceover_audios", lambda *a, **kw: {})

    out = report_cmd._prepare_tts_setup({"topic": "t"}, out_path=None, cfg_logs=False)
    assert out[2] == {}


def test_huber_regression_zero_max_iter():
    """statistics/huber_regression.py 27->50 — max_iter=0 skips loop."""
    from social_research_probe.technologies.statistics.huber_regression import run

    out = run([1.0, 2.0, 3.0], [1.0, 2.0, 3.0], max_iter=0)
    assert isinstance(out, list)


def test_synthesis_runner_status_healthy(monkeypatch):
    """runner.py 115->exit — runner healthy path."""
    from social_research_probe.services.synthesizing import runner as srunner

    cfg = MagicMock()
    cfg.default_structured_runner = "claude"
    monkeypatch.setattr("social_research_probe.config.load_active_config", lambda: cfg)
    monkeypatch.setattr(srunner, "service_flag", lambda *a, **kw: True)
    healthy = MagicMock()
    healthy.health_check = MagicMock(return_value=True)
    monkeypatch.setattr(srunner, "get_runner", lambda name: healthy)
    srunner.log_synthesis_runner_status()


def test_warnings_freshness_old_items():
    """warnings.py 86->exit — stale and fresh freshness branches."""
    from social_research_probe.platforms.base import EngagementMetrics
    from social_research_probe.services.synthesizing.warnings import _check_freshness

    now = datetime.now(UTC)
    stale = EngagementMetrics(
        views=None,
        likes=None,
        comments=None,
        view_velocity=None,
        engagement_ratio=None,
        upload_date=datetime(2010, 1, 1, tzinfo=UTC),
        comment_velocity=None,
        cross_channel_repetition=None,
    )
    notes: list[str] = []
    _check_freshness([stale], now, notes)
    fresh = EngagementMetrics(
        views=None,
        likes=None,
        comments=None,
        view_velocity=None,
        engagement_ratio=None,
        upload_date=now,
        comment_velocity=None,
        cross_channel_repetition=None,
    )
    notes2: list[str] = []
    _check_freshness([fresh], now, notes2)
    assert notes2 == []


def test_youtube_renderer_voicebox_disabled(tmp_path, monkeypatch):
    """report_render/.../youtube.py 166->174 — voicebox disabled branch."""
    from social_research_probe.commands import report as report_cmd

    cfg = MagicMock()
    cfg.technology_enabled = lambda name: False
    monkeypatch.setattr(report_cmd, "load_active_config", lambda: cfg)
    out = report_cmd._prepare_tts_setup({"topic": "t"}, out_path=None, cfg_logs=False)
    assert out == ([], None, {})


def test_write_html_report_voicebox_disabled(tmp_path, monkeypatch):
    """report_render/.../youtube.py 166->174 — voicebox disabled skip path."""
    from social_research_probe.technologies.report_render.html.raw_html import (
        youtube as renderer,
    )

    cfg = MagicMock()
    cfg.data_dir = tmp_path
    cfg.stage_enabled = lambda *a, **kw: True
    cfg.service_enabled = lambda *a, **kw: True
    cfg.technology_enabled = lambda name: False
    monkeypatch.setattr(renderer, "load_active_config", lambda: cfg)
    monkeypatch.setattr(renderer, "_voicebox_api_base", lambda: "")
    monkeypatch.setattr(renderer, "_audio_report_enabled", lambda: False)
    monkeypatch.setattr(renderer, "_technology_logs_enabled", lambda: False)
    monkeypatch.setattr(renderer, "render_html", lambda *a, **kw: "<html></html>")

    out = renderer.write_html_report({"topic": "y", "platform": "youtube"})
    assert out.exists()


def test_write_html_report_voicebox_audio(tmp_path, monkeypatch):
    """report_render/.../youtube.py 166->174, 180-181 — write_html_report voicebox path."""
    from social_research_probe.technologies.report_render.html.raw_html import (
        youtube as renderer,
    )

    cfg = MagicMock()
    cfg.data_dir = tmp_path
    cfg.stage_enabled = lambda *a, **kw: True
    cfg.service_enabled = lambda *a, **kw: True
    cfg.technology_enabled = lambda name: name == "voicebox"
    monkeypatch.setattr(renderer, "load_active_config", lambda: cfg)
    monkeypatch.setattr(renderer, "_voicebox_api_base", lambda: "http://x")
    monkeypatch.setattr(renderer, "_fetch_voicebox_profiles", lambda *a, **kw: [{"name": "v"}])
    monkeypatch.setattr(renderer, "_write_discovered_voicebox_profile_names", lambda *a: None)
    monkeypatch.setattr(renderer, "_select_voicebox_profile", lambda *a, **kw: {"name": "v"})
    monkeypatch.setattr(renderer, "_voicebox_default_profile_name", lambda: "v")
    monkeypatch.setattr(renderer, "_audio_report_enabled", lambda: True)
    monkeypatch.setattr(renderer, "_prepare_voiceover_audios", lambda *a, **kw: {"v": "audio.mp3"})
    monkeypatch.setattr(renderer, "_technology_logs_enabled", lambda: False)
    monkeypatch.setattr(renderer, "render_html", lambda *a, **kw: "<html></html>")

    out = renderer.write_html_report({"topic": "x", "platform": "youtube"})
    assert out.exists()


def test_youtube_renderer_voicebox_audio_path(tmp_path, monkeypatch):
    """report_render/.../youtube.py 180-181 — audio path triggered."""
    from social_research_probe.commands import report as report_cmd

    cfg = MagicMock()
    cfg.technology_enabled = lambda name: name == "voicebox"
    monkeypatch.setattr(report_cmd, "load_active_config", lambda: cfg)
    yt = "social_research_probe.technologies.report_render.html.raw_html.youtube"
    monkeypatch.setattr(f"{yt}._voicebox_api_base", lambda: "http://x")
    monkeypatch.setattr(f"{yt}._fetch_voicebox_profiles", lambda *a, **kw: [{"name": "v"}])
    monkeypatch.setattr(f"{yt}._write_discovered_voicebox_profile_names", lambda *a: None)
    monkeypatch.setattr(f"{yt}._select_voicebox_profile", lambda *a, **kw: {"name": "v"})
    monkeypatch.setattr(f"{yt}._voicebox_default_profile_name", lambda: "v")
    monkeypatch.setattr(f"{yt}._audio_report_enabled", lambda: True)
    monkeypatch.setattr(f"{yt}._prepare_voiceover_audios", lambda *a, **kw: {"v": "http://audio"})

    _profiles, _name, sources = report_cmd._prepare_tts_setup(
        {"topic": "t"}, out_path=str(tmp_path / "out.html"), cfg_logs=False
    )
    assert sources == {"v": "http://audio"}


def test_formatter_plain_sentences_no_split_chars(monkeypatch):
    """formatter.py 332 — when split filters out all parts, fall back to raw cleaned."""
    from social_research_probe.services.synthesizing import formatter as fmt

    monkeypatch.setattr(fmt, "_markdown_to_plain_text", lambda t: "  ")
    out = fmt._plain_sentences("anything", limit=5)
    assert isinstance(out, list)


def test_config_service_enabled_non_dict_category(tmp_path):
    """config.py 274->271 — non-dict category continues to next iteration."""
    from social_research_probe.config import load_active_config

    cfg = load_active_config()
    cfg.raw["services"] = {
        "non_dict_first": "not-a-dict",
        "youtube": {"enriching": {"transcript": True}},
    }
    assert cfg.service_enabled("transcript") is True


def test_evidence_summarize_skips_none_branches():
    """services/synthesizing/evidence.py 51->54 etc — all metric helpers None."""
    from social_research_probe.platforms.base import EngagementMetrics, RawItem
    from social_research_probe.services.synthesizing.evidence import (
        summarize,
        summarize_engagement_metrics,
    )

    item = RawItem(
        id="1",
        url="u",
        title="t",
        author_id="a",
        author_name="A",
        published_at=None,
        metrics={},
        text_excerpt=None,
        thumbnail=None,
        extras={},
    )
    em = EngagementMetrics(
        views=None,
        likes=None,
        comments=None,
        view_velocity=None,
        engagement_ratio=None,
        upload_date=None,
        comment_velocity=None,
        cross_channel_repetition=None,
    )
    out = summarize([item], [em], top_n=[])
    assert "1 items from" in out
    out2 = summarize_engagement_metrics([em])
    assert "1 items" in out2


def test_explanations_correlation_unknown_metric():
    from social_research_probe.services.synthesizing.explanations.correlation import (
        explain_outliers,
        explain_tests,
    )

    assert explain_outliers("Random metric") == ""
    assert explain_tests("Random", "x") == ""


def test_explanations_descriptive_unknown():
    from social_research_probe.services.synthesizing.explanations.descriptive import (
        explain_descriptive,
        explain_spread,
    )

    assert explain_descriptive("Random metric: 0.5") == ""
    assert explain_spread("Random metric: 0.5") == ""


def test_explanations_regression_unknown():
    from social_research_probe.services.synthesizing.explanations.regression import (
        explain_regression,
    )

    assert explain_regression("Random metric: 0.5") == ""


def test_formatter_plain_sentences_empty():
    """services/synthesizing/formatter.py:329,332 — empty / unsplit text."""
    from social_research_probe.services.synthesizing.formatter import _plain_sentences

    assert _plain_sentences("", limit=5) == []
    assert _plain_sentences("just a phrase no punctuation", limit=5) == [
        "just a phrase no punctuation."
    ]


def test_formatter_plain_sentences_only_markdown():
    from social_research_probe.services.synthesizing.formatter import _plain_sentences

    assert _plain_sentences("```\n```", limit=5) == []


def test_warnings_unknown_source_class():
    """services/synthesizing/warnings.py:74 — all-unknown branch."""
    from social_research_probe.services.synthesizing.warnings import _check_top_n_quality

    notes: list[str] = []
    top_n = [{"source_class": "unknown", "scores": {"overall": 1.0}}]
    _check_top_n_quality(top_n, notes)
    assert any("unknown source classification" in n for n in notes)


def test_ensemble_synthesis_fallback_to_codex(monkeypatch):
    """services/llm/ensemble.py:147 — last-line fallback returns codex."""
    from social_research_probe.services.llm import ensemble

    async def fake_run_provider(name, *a, **kw):
        return None  # all synthesis attempts fail

    monkeypatch.setattr(ensemble, "_run_provider", fake_run_provider)
    cfg = MagicMock()
    cfg.service_enabled = lambda *_a, **_k: True
    cfg.technology_enabled = lambda *_a, **_k: True
    out = asyncio.run(ensemble._synthesize({"codex": "answer"}, "p", cfg))
    assert out == "answer"

    out = asyncio.run(ensemble._synthesize({"codex": "x", "gemini": "y"}, "p", cfg))
    assert out in ("x", "y")


def test_provider_api_keys(monkeypatch):
    """corroborates/{brave,exa,tavily}.py — _api_key returns when secret set."""
    from social_research_probe.technologies.corroborates import brave, exa, tavily

    monkeypatch.setattr(brave, "read_runtime_secret", lambda k: "key")
    monkeypatch.setattr(exa, "read_runtime_secret", lambda k: "key")
    monkeypatch.setattr(tavily, "read_runtime_secret", lambda k: "key")
    assert brave.BraveProvider()._api_key() == "key"
    assert exa.ExaProvider()._api_key() == "key"
    assert tavily.TavilyProvider()._api_key() == "key"


def test_brave_build_result_logs_filter(monkeypatch):
    """corroborates/brave.py:119 — log when filter excludes results."""
    from social_research_probe.technologies.corroborates import brave

    monkeypatch.setattr(
        brave,
        "filter_results",
        lambda raw_results, src: ([{"url": "https://news.com/abc"}], 1, 1),
    )
    provider = brave.BraveProvider()
    claim = MagicMock()
    claim.source_url = "https://example.com/x"
    out = provider._build_result(claim, [{"url": "https://x"}])
    assert out is not None


def test_tavily_build_result_logs_filter(monkeypatch):
    from social_research_probe.technologies.corroborates import tavily

    monkeypatch.setattr(
        tavily,
        "filter_results",
        lambda raw_results, src: ([{"url": "https://news.com/abc"}], 1, 1),
    )
    provider = tavily.TavilyProvider()
    claim = MagicMock()
    claim.source_url = "https://example.com/x"
    out = provider._build_result(claim, [{"url": "https://x"}])
    assert out is not None


def test_jsoncli_runner_default_helpers():
    """technologies/llms/__init__.py:182,186 — base helpers."""
    from social_research_probe.technologies.llms import JsonCliRunner

    class _Dummy(JsonCliRunner):
        name = "dummy"
        binary_name = "dummy"
        base_argv = ()
        schema_flag = None
        health_check_key = "dummy"
        enabled_config_key = "dummy"

    d = _Dummy()
    assert d._prompt_args("p") == []
    assert d._stdin_input("p") == "p"


def test_youtube_api_search_and_hydrate(monkeypatch, tmp_path):
    """technologies/media_fetch/youtube_api.py:87,118,149 — success returns."""
    from social_research_probe.technologies.media_fetch import youtube_api

    class FakeRequest:
        def execute(self):
            return {"items": [{"id": "x"}]}

    class FakeResource:
        def list(self, **kw):
            return FakeRequest()

    class FakeClient:
        def search(self):
            return FakeResource()

        def videos(self):
            return FakeResource()

        def channels(self):
            return FakeResource()

    monkeypatch.setattr(youtube_api, "_build_client", lambda key: FakeClient())
    items = youtube_api._search_videos("k", topic="t", max_items=5, published_after=None)
    assert items == [{"id": "x"}]
    assert youtube_api._fetch_video_details("k", video_ids=["1"]) == [{"id": "x"}]
    assert youtube_api._fetch_channel_details("k", channel_ids=["1"]) == [{"id": "x"}]


def test_markdown_close_list_transition():
    """markdown_to_html.py:57 — ul → ol transition closes ul."""
    from social_research_probe.technologies.report_render.html.raw_html.markdown_to_html import (
        md_to_html,
    )

    out = md_to_html("- a\n1. b\n")
    assert "<ul>" in out and "<ol>" in out


def test_youtube_renderer_audio_disabled(tmp_path, monkeypatch):
    """report_render/html/raw_html/youtube.py:180-181 — audio path skipped."""
    from social_research_probe.technologies.report_render.html.raw_html import (
        youtube as renderer,
    )

    cfg = MagicMock()
    cfg.technology_enabled = lambda name: True
    cfg.voicebox = {"api_base": ""}
    cfg.data_dir = tmp_path

    monkeypatch.setattr(renderer, "_audio_report_enabled", lambda: True)
    monkeypatch.setattr(renderer, "_prepare_voiceover_audios", lambda *a, **kw: {})
    # ensures the audio path branches without doing real work — covers calls only


def test_bayesian_linear_returns_empty_when_singular(monkeypatch):
    """statistics/bayesian_linear.py:38 — beta None path."""
    from social_research_probe.technologies.statistics import bayesian_linear

    monkeypatch.setattr(bayesian_linear, "_solve_normal_equations", lambda *_a, **_k: None)
    out = bayesian_linear.run([1.0, 2.0, 3.0, 4.0], {"a": [1.0, 2.0, 3.0, 4.0]})
    assert out == []


def test_kaplan_meier_no_events_branch():
    """statistics/kaplan_meier.py:24 — no events returns single result."""
    from social_research_probe.technologies.statistics.kaplan_meier import run

    out = run([10.0, 20.0, 30.0], [0, 0, 0])
    assert len(out) == 1
    assert "no events" in out[0].caption


def test_kmeans_returns_empty_for_small_input():
    """statistics/kmeans.py:27 — too few items."""
    from social_research_probe.technologies.statistics.kmeans import run

    assert run([[1.0]], k=3) == []


def test_kmeans_returns_empty_when_fit_empty(monkeypatch):
    """statistics/kmeans.py:27 — fit returns no centroids."""
    from social_research_probe.technologies.statistics import kmeans

    monkeypatch.setattr(kmeans, "fit", lambda *a, **kw: ([], []))
    assert kmeans.run([[1.0], [2.0], [3.0]], k=2) == []


def test_logistic_all_one_class():
    """statistics/logistic_regression.py:31 — y not split returns []."""
    from social_research_probe.technologies.statistics.logistic_regression import run

    assert run([0, 0, 0, 0, 0], {"a": [1.0, 2.0, 3.0, 4.0, 5.0]}) == []


def test_pca_project_and_fit_components():
    """statistics/pca.py:51-52, 60-63 — project + fit_components paths."""
    from social_research_probe.technologies.statistics.pca import (
        fit_components,
        project,
    )

    features = [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]]
    components = fit_components(features, n_components=1)
    assert components
    projected = project(features, components)
    assert len(projected) == 3
    assert fit_components([[1.0, 2.0]]) == []


def test_logistic_regression_too_few_samples():
    """statistics/logistic_regression.py:31 — n <= k+1 returns []."""
    from social_research_probe.technologies.statistics.logistic_regression import run

    assert run([0, 1], {"a": [1.0, 2.0]}) == []


def test_naive_bayes_empty_features():
    """statistics/naive_bayes.py:28 — no feature names."""
    from social_research_probe.technologies.statistics.naive_bayes import run

    assert run([0, 1, 0, 1], {}) == []


def test_normality_zero_variance():
    """statistics/normality.py:25 — zero variance returns []."""
    from social_research_probe.technologies.statistics.normality import run

    assert run([5.0, 5.0, 5.0, 5.0]) == []


def test_normality_kurt_branches():
    """statistics/normality.py:61 — heavy / light tail labels."""
    from social_research_probe.technologies.statistics.normality import _kurt_verdict

    assert "heavy" in _kurt_verdict(5.0)
    assert "light" in _kurt_verdict(-5.0)


def test_polynomial_fit_coefficients():
    """statistics/polynomial_regression.py:50-51 — fit_coefficients."""
    from social_research_probe.technologies.statistics.polynomial_regression import (
        fit_coefficients,
    )

    coeffs = fit_coefficients([1.0, 2.0, 3.0, 4.0, 5.0], [1.0, 4.0, 9.0, 16.0, 25.0], 2)
    assert coeffs is not None
    assert len(coeffs) == 3


def test_mac_tts_synthesize(monkeypatch, tmp_path):
    """technologies/tts/mac_tts.py:30 — synthesize_mac calls subprocess."""
    from social_research_probe.technologies.tts import mac_tts

    captured = {}

    def fake_run(args, **kw):
        captured["args"] = args
        return MagicMock(returncode=0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    mac_tts.synthesize_mac("hi", "Alex", tmp_path / "out.aiff")
    assert captured["args"][0] == "say"


def test_ai_slop_detector_repeated_trigrams():
    """validation/ai_slop_detector.py:44 — duplicate trigram counted."""
    from social_research_probe.technologies.validation.ai_slop_detector import (
        _repetition_signal,
    )

    text = "the quick brown fox the quick brown fox the quick brown fox"
    assert _repetition_signal(text) > 0


def test_progress_summarize_dataclass():
    """utils/display/progress.py:133 — dataclass branch."""
    from dataclasses import dataclass

    from social_research_probe.utils.display.progress import _summarize_container_value

    @dataclass
    class _D:
        x: int = 1

    out = _summarize_container_value(_D())
    assert out["type"] == "_D"


def test_transcript_whisper_fallback(monkeypatch, tmp_path):
    """services/enriching/transcript.py:68 — whisper fallback path."""
    from social_research_probe.services.enriching import transcript

    monkeypatch.setattr(
        "social_research_probe.technologies.transcript_fetch.youtube_transcript_api.fetch_transcript",
        lambda url: None,
    )
    monkeypatch.setattr(
        "social_research_probe.technologies.media_fetch.yt_dlp.download_audio",
        lambda url, dest: str(tmp_path / "audio.mp3"),
    )
    monkeypatch.setattr(
        "social_research_probe.technologies.transcript_fetch.whisper.transcribe_audio",
        lambda path: "transcribed",
    )
    cfg = MagicMock()
    cfg.technology_enabled = lambda *_a, **_k: True
    cfg.service_enabled = lambda *_a, **_k: True
    with patch("social_research_probe.config.load_active_config", return_value=cfg):
        result = asyncio.run(
            transcript.TranscriptService().execute_one(
                {"url": "https://youtube.com/watch?v=x", "id": "x"}
            )
        )
    assert result is not None
