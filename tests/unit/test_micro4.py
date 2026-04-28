"""Final micro coverage."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from social_research_probe.commands import config as cfg_cmd
from social_research_probe.commands import install_skill
from social_research_probe.config import Config
from social_research_probe.platforms.youtube import pipeline as yt
from social_research_probe.services.enriching import transcript as transcript_svc
from social_research_probe.technologies.llms import ensemble
from social_research_probe.services.synthesizing.synthesis.helpers.contextual_models import (
    explain_correlation,
    explain_descriptive,
)
from social_research_probe.technologies.statistics import (
    bayesian_linear,
    huber_regression,
    normality,
    polynomial_regression,
)
from social_research_probe.technologies.validation.ai_slop_detector import score


class TestConfigPreferredFreeText:
    def test_unknown_runner(self, tmp_path):
        (tmp_path / "config.toml").write_text('[llm]\nrunner = "weird-runner"\n')
        cfg = Config.load(tmp_path)
        # service enabled defaults true, runner not in known set
        assert cfg.preferred_free_text_runner is None


class TestConfigDefaultStructured:
    def test_runner_disabled_returns_none(self, tmp_path):
        (tmp_path / "config.toml").write_text(
            '[llm]\nrunner = "claude"\n[technologies]\nclaude = false\n'
        )
        cfg = Config.load(tmp_path)
        assert cfg.default_structured_runner == "none"


class TestConfigAllowsBranches:
    def test_allows_no_stage_no_service(self, tmp_path):
        cfg = Config.load(tmp_path)
        # All None → True
        assert cfg.allows() is True

    def test_allows_service_disabled(self, tmp_path):
        cfg = Config.load(tmp_path)
        # service "missing" returns False
        assert cfg.allows(service="missing") is False


class TestCmdConfigEmitTable:
    def test_emit_table_with_nested(self):
        lines: list[str] = []
        cfg_cmd._emit_table("a", {"x": 1, "nested": {"y": 2}}, lines)
        assert any("[a]" in line for line in lines)
        assert any("[a.nested]" in line for line in lines)


class TestCmdConfigOrderLikeTemplate:
    def test_template_ordering_with_extra(self):
        out = cfg_cmd._order_like_template({"a": 1, "b": {"x": 2}, "c": 3}, {"b": {"x": 0}, "a": 0})
        assert list(out.keys()) == ["b", "a", "c"]


class TestCmdConfigFormatSecretsSection:
    def test_with_env(self, monkeypatch):
        monkeypatch.setenv("SRP_API_KEY", "envvalue1234")
        out = cfg_cmd._format_secrets_section({"api_key": "filevalue"})
        assert any("from env" in line for line in out)


class TestPipelineYtCorroborateValidationError:
    def test_provider_health_error(self, monkeypatch):
        cfg = MagicMock()
        cfg.service_enabled.return_value = True
        cfg.corroboration_provider = "exa"
        cfg.technology_enabled.return_value = True
        provider = MagicMock()
        provider.health_check.side_effect = RuntimeError("hard err")
        with (
            patch("social_research_probe.config.load_active_config", return_value=cfg),
            patch(
                "social_research_probe.services.corroborating.get_provider",
                return_value=provider,
            ),
        ):
            # health_check raises non-ValidationError → propagates? No, only catches ValidationError
            with pytest.raises(RuntimeError):
                yt.YouTubeCorroborateStage()._select_corroboration_providers()


class TestNormalitySkewVerdict:
    def test_skew_verdicts(self):
        # left, right, near-symmetric
        assert "right-skewed" in normality._skew_verdict(0.8)
        assert "left-skewed" in normality._skew_verdict(-0.8)
        assert "approximately symmetric" in normality._skew_verdict(0.0)


class TestLogisticOverflowBranches:
    def test_or_str_huge_pos(self, monkeypatch):
        # Force coeff > 500 in formatted output → "odds ratio > 1e217"

        def fake_runner(prompt, **kw):
            return {"answer": "x"}

        # call the format helper directly
        from social_research_probe.technologies.statistics import logistic_regression as lr

        out = lr._format_results(
            y=[0, 1],
            x=[[1.0, 600.0], [1.0, -600.0]],
            beta=[0.0, 1000.0],
            names=["x"],
            label="y",
        )
        captions = [r.caption for r in out]
        assert any("> 1e217" in c for c in captions)

    def test_or_str_huge_neg(self):
        from social_research_probe.technologies.statistics import logistic_regression as lr

        out = lr._format_results(
            y=[0, 1],
            x=[[1.0, 600.0], [1.0, -600.0]],
            beta=[0.0, -1000.0],
            names=["x"],
            label="y",
        )
        assert any("< 1e-217" in r.caption for r in out)


class TestPolynomialBigDegree:
    def test_negative_degree(self):
        assert (
            polynomial_regression.fit_coefficients([1.0, 2.0, 3.0], [1.0, 2.0, 3.0], degree=0)
            is None
        )


class TestBayesianRunNoFeatures:
    def test_zero_columns(self):
        # Zero feature columns case
        out = bayesian_linear.run([1.0, 2.0, 3.0], {})
        assert isinstance(out, list)


class TestHuberRegressionTooFew:
    def test_too_few_points(self):
        assert huber_regression.run([1.0], [1.0]) == []


class TestExplainCorrelationNoFactors:
    def test_no_factor_match_return(self):
        out = explain_correlation("Pearson r blah: -0.6")
        # branch where pair defaults to "these two factors"
        assert "these two factors" in out


class TestExplainDescriptiveMaxBranch:
    def test_max(self):
        assert "Ceiling" in explain_descriptive("Max overall: 0.95")


class TestSlopScoreEdge:
    def test_score_blank_returns_zero(self):
        assert score("   ") == 0.0


class TestEnsembleSecondaryDisabled:
    def test_service_enabled_secondary_disabled(self):
        cfg = MagicMock()
        cfg.service_enabled.return_value = True
        cfg.technology_enabled.return_value = False
        cfg.llm_runner = "claude"
        # Secondary returns False because tech disabled
        assert ensemble._service_enabled(cfg, "gemini") is False


class TestTranscriptServiceWithStringInput:
    def test_string_input(self, monkeypatch):
        from social_research_probe.technologies.transcript_fetch.youtube_transcript_api import (
            YoutubeTranscriptFetch,
        )

        async def fake_exec(self, data):
            return None

        monkeypatch.setattr(YoutubeTranscriptFetch, "execute", fake_exec)
        monkeypatch.setattr(
            "social_research_probe.technologies.media_fetch.yt_dlp.download_audio",
            lambda u, t: None,
        )
        out = asyncio.run(transcript_svc.TranscriptService().execute_one("https://x"))
        assert out.input_key == "https://x"


class TestInstallSkillEnsureVoiceboxExisting:
    def test_existing_secret(self, monkeypatch, tmp_path):
        with patch("social_research_probe.commands.config.read_secret", return_value="set"):
            install_skill._ensure_voicebox_secrets()
