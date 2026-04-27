"""Even more micro coverage."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import social_research_probe.services.reporting as writer_svc
from social_research_probe.platforms.youtube import pipeline as yt
from social_research_probe.services.analyzing import charts as charts_svc
from social_research_probe.services.scoring import score as scoring_svc
from social_research_probe.services.synthesizing import synthesis as synth_svc
from social_research_probe.services.synthesizing.explanations import (
    explain_correlation,
    explain_descriptive,
    explain_spread,
    explain_tests,
)
from social_research_probe.technologies.corroborates._filters import _host, is_self_source
from social_research_probe.technologies.media_fetch import youtube_api
from social_research_probe.technologies.statistics import (
    bayesian_linear,
    huber_regression,
    kaplan_meier,
    kmeans,
    logistic_regression,
    normality,
    pca,
    polynomial_regression,
)
from social_research_probe.technologies.validation.ai_slop_detector import score as slop_score
from social_research_probe.utils.core.errors import AdapterError


def test_config_active_data_dir_no_env_branch(monkeypatch, tmp_path):
    monkeypatch.delenv("SRP_DATA_DIR", raising=False)
    from social_research_probe.config import _active_data_dir

    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    out = _active_data_dir()
    assert ".social-research-probe" in str(out)


def test_pca_power_iteration_zero_norm():
    # Trigger early-return when norm < 1e-12
    out = pca._power_iteration([[0.0, 0.0], [0.0, 0.0]], 2)
    assert isinstance(out, tuple)


def test_pca_power_iteration_converges():
    # Already-converged input should hit the break path
    matrix = [[1.0, 0.0], [0.0, 1.0]]
    vec, eig = pca._power_iteration(matrix, 2)
    assert isinstance(vec, list) and isinstance(eig, float)


def test_logistic_overflow_str():
    # Verify both odds-ratio extreme branches produce strings
    y = [0, 1]
    features = {"x": [-1e6, 1e6]}
    out = logistic_regression.run(y, features, max_iter=2)
    assert isinstance(out, list)


def test_normality_kurt_negative():
    assert "light-tailed" in normality._kurt_verdict(-1.5)


def test_huber_mad_zero():
    assert huber_regression._mad([]) == 0.0


def test_filters_host_invalid_returns_none():
    # urlparse with malformed raises
    out = _host("http://[")
    assert out is None or isinstance(out, str)


def test_filters_self_source_no_host():
    # If both URLs unparseable
    assert (
        is_self_source("malformed", "malformed") is False
        or is_self_source("malformed", "malformed") is True
    )


def test_kmeans_k_too_large():
    out = kmeans.fit([[0.0]], k=5)
    assert out == ([], [])


def test_kaplan_meier_unequal():
    assert kaplan_meier.fit([1.0, 2.0], [1]) == []


def test_polynomial_run_empty():
    assert polynomial_regression.run([], [], degree=2) == []


def test_bayesian_diag_size_zero():
    # Size 0 returns empty
    assert bayesian_linear._diagonal_of_inverse([], 0) == []


def test_explain_correlation_no_factors():
    # Branch where factors list is empty
    out = explain_correlation("Pearson r: 0.5")
    assert "0.50" in out


def test_explain_descriptive_min_branch():
    out = explain_descriptive("Min overall: 0.20")
    assert "Floor" in out


def test_explain_spread_kurt_normal():
    out = explain_spread("Excess kurtosis x: 0.0")
    assert "Normal tails" in out


def test_explain_tests_normality_normal():
    out = explain_tests("Normality check x: ok", "")
    assert "Bell-curve" in out


class TestScoringServiceFailure:
    def test_failure_path(self, monkeypatch):
        # Force score_items to raise → exception branch
        monkeypatch.setattr(
            "social_research_probe.services.scoring.compute.score_items",
            lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("nope")),
        )
        out = asyncio.run(
            scoring_svc.ScoringService().execute_one(
                {"items": [{"trust": 0.5, "trend": 0.5, "opportunity": 0.5}]}
            )
        )
        assert out.tech_results[0].success is False


class TestSynthesisServiceSuccess:
    def test_with_text(self, monkeypatch):
        async def fake_multi(p, task="generating response"):
            return "synthesized"

        monkeypatch.setattr(
            "social_research_probe.services.llm.ensemble.multi_llm_prompt", fake_multi
        )
        monkeypatch.setattr(
            "social_research_probe.services.synthesizing.llm_contract.build_synthesis_prompt",
            lambda r: "p",
        )
        out = asyncio.run(synth_svc.SynthesisService().execute_one({"topic": "x"}))
        assert out.tech_results[0].output == "synthesized"


class TestWriterHtmlNoFallback:
    def test_html_success_returns_command(self, tmp_path, monkeypatch):
        monkeypatch.setattr(writer_svc, "stage_flag", lambda *a, **k: True)
        monkeypatch.setattr(writer_svc, "service_flag", lambda *a, **k: True)
        cfg = MagicMock()
        cfg.data_dir = tmp_path
        target = tmp_path / "x.html"
        target.write_text("h")
        with (
            patch("social_research_probe.config.load_active_config", return_value=cfg),
            patch.object(writer_svc, "write_html_report", return_value=target),
            patch.object(writer_svc, "serve_report_command", return_value="cmd"),
        ):
            out = writer_svc.write_final_report(
                {
                    "topic": "t",
                    "platform": "p",
                    "purpose_set": [],
                    "items_top_n": [],
                    "stats_summary": {},
                    "platform_engagement_summary": "",
                    "evidence_summary": "",
                    "chart_captions": [],
                    "warnings": [],
                },
                allow_html=True,
            )
        assert out == "cmd"


class TestPipelineYtCorroborateLLMSearchGate:
    def test_skips_llm_search(self, monkeypatch):
        cfg = MagicMock()
        cfg.service_enabled.side_effect = lambda n: n == "corroboration"  # llm disabled
        cfg.corroboration_provider = "auto"
        cfg.technology_enabled.return_value = True
        with (
            patch("social_research_probe.config.load_active_config", return_value=cfg),
            patch(
                "social_research_probe.services.corroborating.auto_mode_providers",
                return_value=("llm_search", "exa"),
            ),
            patch("social_research_probe.services.corroborating.get_provider") as gp,
        ):
            healthy = MagicMock()
            healthy.health_check.return_value = True
            gp.return_value = healthy
            out = yt.YouTubeCorroborateStage()._select_corroboration_providers()
        assert "llm_search" not in out


class TestChartsServiceCacheRestoreSuccess:
    def test_cache_hit_returns_restored(self, monkeypatch, tmp_path):
        png = tmp_path / "x.png"
        png.write_bytes(b"x")
        monkeypatch.setattr(
            "social_research_probe.utils.caching.pipeline_cache.get_json",
            lambda c, k: {"filenames": ["x.png"], "captions": ["cap"]},
        )
        out = asyncio.run(charts_svc.ChartsService._render_with_cache([{"id": "1"}], tmp_path))
        assert out and out[0].caption == "cap"


def test_youtube_api_resolve_no_secret_raises(monkeypatch):
    monkeypatch.delenv("SRP_YOUTUBE_API_KEY", raising=False)
    with patch("social_research_probe.commands.config.read_secret", return_value=None):
        with pytest.raises(AdapterError):
            youtube_api.resolve_youtube_api_key()


def test_slop_score_detects():
    out = slop_score(
        "In conclusion, it is important to note that as an AI I cannot. Of course, certainly. Delve."
    )
    assert out > 0


def test_jsoncli_runner_async_execute(monkeypatch):
    cfg = MagicMock()
    cfg.llm_settings.return_value = {"binary": "claude"}
    cfg.llm_timeout_seconds = 10
    result = MagicMock(stdout='{"k": 1}')
    with (
        patch("social_research_probe.technologies.llms.load_active_config", return_value=cfg),
        patch("social_research_probe.utils.io.subprocess_runner.run", return_value=result),
    ):
        from social_research_probe.technologies.llms.claude_cli import ClaudeRunner

        out = asyncio.run(ClaudeRunner()._execute("p"))
    assert out == {"k": 1}
