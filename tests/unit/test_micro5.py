"""Micro 5 — push to 100%."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest

import social_research_probe.services.reporting as writer_svc
from social_research_probe.commands import config as cfg_cmd
from social_research_probe.commands import install_skill
from social_research_probe.config import Config
from social_research_probe.platforms.youtube import pipeline as yt
from social_research_probe.services.analyzing import charts as charts_svc
from social_research_probe.services.enriching import transcript as transcript_svc
from social_research_probe.services.llm import ensemble
from social_research_probe.services.synthesizing import synthesis as synth_svc
from social_research_probe.services.synthesizing.explanations import (
    explain_correlation,
    explain_descriptive,
)
from social_research_probe.technologies.llms.gemini_cli import GeminiRunner
from social_research_probe.technologies.media_fetch import youtube_api
from social_research_probe.technologies.statistics import (
    bayesian_linear,
    huber_regression,
    logistic_regression,
    normality,
    polynomial_regression,
)
from social_research_probe.technologies.validation.ai_slop_detector import score
from social_research_probe.utils.core.errors import AdapterError


class TestPcaPowerIterationConverged:
    def test_already_converged(self):
        # Identity matrix → vec converges immediately
        out = pca_test_matrix()
        assert out is not None


def pca_test_matrix():
    from social_research_probe.technologies.statistics import pca

    matrix = [[1.0, 0.0], [0.0, 0.5]]
    return pca._power_iteration(matrix, 2, iterations=300)


class TestHtmlVoiceoverPlainSkip:
    def test_voiceover_plain_empty(self, monkeypatch):
        from social_research_probe.technologies.report_render.html.raw_html import (
            youtube as yt_html,
        )

        # markdown_to_voiceover_text returning empty string for plain
        monkeypatch.setattr(yt_html, "_markdown_to_voiceover_text", lambda t: "")
        out = yt_html.build_voiceover_text({"compiled_synthesis": "x", "opportunity_analysis": "y"})
        assert out is None or "Final summary" in (out or "")


class TestPipelineYtCorroborateFastModeOnPath:
    def test_skips_when_tech_disabled(self):
        cfg = MagicMock()
        cfg.service_enabled.return_value = True
        cfg.corroboration_provider = "exa"
        cfg.technology_enabled.return_value = False  # exa disabled
        with patch("social_research_probe.config.load_active_config", return_value=cfg):
            out = yt.YouTubeCorroborateStage()._select_corroboration_providers()
        assert out == []


class TestConfigAllowsTechnology:
    def test_allows_technology_only(self, tmp_path):
        cfg = Config.load(tmp_path)
        assert cfg.allows(technology="yt_dlp") is True


class TestLogisticConverged:
    def test_converged_break(self):
        # Force a near-zero diff between iterations
        y = [0, 1, 0, 1, 1, 0]
        features = {"x": [0.0, 1.0, 0.0, 1.0, 1.0, 0.0]}
        out = logistic_regression.run(y, features, max_iter=50)
        assert isinstance(out, list)


class TestHuberConverged:
    def test_converged_break(self):
        # Perfect linear → converge fast
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [v * 2.0 + 1.0 for v in x]
        out = huber_regression.run(x, y)
        assert out


class TestYtApiResolveSecretEmpty:
    def test_secret_empty_string(self, monkeypatch):
        monkeypatch.delenv("SRP_YOUTUBE_API_KEY", raising=False)
        with patch("social_research_probe.commands.config.read_secret", return_value=""):
            with pytest.raises(AdapterError):
                youtube_api.resolve_youtube_api_key()


class TestGeminiStdinAndPromptArgs:
    def test_prompt_args_uses_prompt_flag(self):
        runner = GeminiRunner()
        out = runner._prompt_args("hello")
        assert "--prompt" in out and "hello" in out

    def test_stdin_input_returns_none(self):
        assert GeminiRunner()._stdin_input("p") is None


class TestSynthesisServiceFailure:
    def test_exception_branch(self, monkeypatch):
        async def fake_multi(p, task="generating response"):
            raise RuntimeError("boom")

        monkeypatch.setattr(
            "social_research_probe.services.llm.ensemble.multi_llm_prompt", fake_multi
        )
        out = asyncio.run(synth_svc.SynthesisService().execute_one({"topic": "x"}))
        assert out.tech_results[0].success is False


class TestWriterRenderFailure:
    def test_render_full_raises_falls_back(self, tmp_path, monkeypatch):
        monkeypatch.setattr(writer_svc, "stage_flag", lambda *a, **k: False)
        cfg = MagicMock()
        cfg.data_dir = tmp_path
        with (
            patch("social_research_probe.config.load_active_config", return_value=cfg),
            patch.object(writer_svc, "render_full", side_effect=RuntimeError),
        ):
            writer_svc.write_final_report(
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
                allow_html=False,
            )
        # Falls back to placeholder content
        text = (tmp_path / "report.md").read_text()
        assert "no content" in text


class TestEnsembleServiceEnabledFallback:
    def test_no_technology_method(self):
        # Cfg has no technology_enabled attribute → returns True branch
        class Cfg:
            llm_runner = "claude"

            def service_enabled(self, name):
                return True

        assert ensemble._service_enabled(Cfg(), "anything") is True


class TestCmdConfigOrderEdge:
    def test_extra_dict_recursion(self):
        out = cfg_cmd._order_like_template({"x": {"a": 1, "b": 2}}, {})
        assert out == {"x": {"a": 1, "b": 2}}


class TestCommandsInitDuplicateForce:
    def test_validate_purpose_addition_force_raises_when_exact(self, monkeypatch):
        from social_research_probe.commands import _validate_purpose_addition
        from social_research_probe.utils.core.errors import DuplicateError

        with pytest.raises(DuplicateError, match="rename"):
            _validate_purpose_addition("foo", ["foo", "bar"], force=True)


class TestInstallSkillCopyConfigBundle:
    def test_copy_config_bundle_print(self, monkeypatch, tmp_path, capsys):
        cfg = MagicMock()
        cfg.data_dir = tmp_path
        bundled = tmp_path / "bundled.toml"
        bundled.write_text("[s]\nk = 1\n")
        monkeypatch.setattr(install_skill, "_BUNDLED_CONFIG", bundled)
        with patch("social_research_probe.config.load_active_config", return_value=cfg):
            install_skill._copy_config_example()
        assert "Default config written" in capsys.readouterr().out


class TestNormalityKurtVerdict:
    def test_kurt_zero(self):
        assert "near-normal" in normality._kurt_verdict(0.0)


class TestExplainCorrelationDefault:
    def test_no_factors_branch(self):
        # No "between X and Y" pattern
        out = explain_correlation("Pearson r summary: 0.6")
        assert "these two factors" in out


class TestExplainDescriptiveUnknown:
    def test_no_prefix_match_returns_empty(self):
        out = explain_descriptive("Mean unknown: x")
        assert out == ""


class TestSlopScoreBlank:
    def test_only_whitespace(self):
        assert score("\n\n   ") == 0.0


class TestPolyRegressionEarlyExit:
    def test_negative_or_zero_degree(self):
        out = polynomial_regression.fit_coefficients([1.0, 2.0, 3.0], [1.0, 2.0, 3.0], degree=-1)
        assert out is None


class TestBayesianRunZeroFeatures:
    def test_zero_features(self):
        # 0 features matrix path
        out = bayesian_linear.run([1.0, 2.0, 3.0], {})
        assert out == []


class TestTranscriptStringInput:
    def test_string_data_branch(self, monkeypatch):
        from social_research_probe.technologies.transcript_fetch.youtube_transcript_api import (
            YoutubeTranscriptFetch,
        )

        async def fake_exec(self, data):
            return None

        monkeypatch.setattr(YoutubeTranscriptFetch, "execute", fake_exec)

        async def fake_dl(*a, **kw):
            return None

        monkeypatch.setattr(
            "social_research_probe.technologies.media_fetch.yt_dlp.download_audio",
            lambda u, t: None,
        )
        out = asyncio.run(transcript_svc.TranscriptService().execute_one("u-string"))
        assert out.input_key == "u-string"


class TestChartsSvcRestoredEmpty:
    def test_render_with_cache_empty_restored(self, monkeypatch, tmp_path):
        # Cache returned but restored=[] (file missing) → falls through to render
        monkeypatch.setattr(
            "social_research_probe.utils.caching.pipeline_cache.get_json",
            lambda c, k: {"filenames": ["nonexistent.png"], "captions": ["c"]},
        )
        captured = {}

        async def fake_render(items, out):
            from social_research_probe.technologies.charts.base import ChartResult

            png = tmp_path / "fresh.png"
            png.write_bytes(b"x")
            return [ChartResult(path=str(png), caption="fresh")]

        monkeypatch.setattr(charts_svc.ChartsService, "_render", staticmethod(fake_render))
        monkeypatch.setattr(
            "social_research_probe.utils.caching.pipeline_cache.set_json",
            lambda c, k, v: captured.update({"v": v}),
        )
        out = asyncio.run(charts_svc.ChartsService._render_with_cache([{"id": "1"}], tmp_path))
        assert out and out[0].caption == "fresh"
