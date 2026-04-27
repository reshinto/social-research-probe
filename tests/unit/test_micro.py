"""Cover micro gaps for 100%."""

from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from social_research_probe.platforms.youtube import pipeline as yt
from social_research_probe.services.synthesizing.explanations import explain_spearman
from social_research_probe.technologies.charts import histogram
from social_research_probe.technologies.corroborates import _filters
from social_research_probe.technologies.media_fetch import yt_dlp
from social_research_probe.technologies.statistics import (
    bayesian_linear,
    huber_regression,
    naive_bayes,
    normality,
)
from social_research_probe.technologies.transcript_fetch import whisper as whisper_mod


class TestWhisperExecute:
    def test_failure_raises(self, monkeypatch):
        monkeypatch.setattr(whisper_mod, "transcribe_audio", lambda p, model_name="base": None)
        with pytest.raises(RuntimeError):
            asyncio.run(whisper_mod.WhisperTranscript()._execute(Path("/tmp/x.mp3")))

    def test_success(self, monkeypatch):
        monkeypatch.setattr(whisper_mod, "transcribe_audio", lambda p, model_name="base": "tx")
        out = asyncio.run(whisper_mod.WhisperTranscript()._execute(Path("/tmp/audio.mp3")))
        assert out == {"audio.mp3": "tx"}


class TestYtDlpBrowser:
    def test_browser_env(self, monkeypatch, tmp_path):
        captured = {}

        def fake_run(cmd, **kw):
            captured["cmd"] = cmd
            return MagicMock(returncode=1, stderr="")

        monkeypatch.setenv("SRP_YTDLP_BROWSER", "chrome")
        monkeypatch.delenv("SRP_YTDLP_COOKIES_FILE", raising=False)
        monkeypatch.setattr(subprocess, "run", fake_run)
        yt_dlp.download_audio("u", str(tmp_path))
        assert "--cookies-from-browser" in captured["cmd"]


class TestNormalityKurt:
    def test_light_tailed(self):
        assert "light-tailed" in normality._kurt_verdict(-1.5)


class TestHuberWeight:
    def test_clamp_outside(self):
        # _huber_weight scaled_residual outside k → returns k/abs_r
        assert huber_regression._huber_weight(2.0, 1.345) < 1.0


class TestBayesianAddSize:
    def test_diag_inverse_size_too_small(self):
        # tests early return path for _diagonal_of_inverse
        out = bayesian_linear._diagonal_of_inverse([[1.0]], 0)
        assert out == []


class TestNaiveBayesEdge:
    def test_zero_values(self):
        _priors, _mus, sigmas = naive_bayes.fit(["a"], {"x": [1.0]})
        assert sigmas["a"]["x"] == 1.0


class TestFiltersHostInvalid:
    def test_host_url_with_port(self):
        # _host should successfully parse with port
        assert _filters._host("https://x.com:8080/p") == "x.com"


class TestExplainSpearmanEdge:
    def test_no_factors(self):
        out = explain_spearman("Spearman rho: 0.6")
        assert isinstance(out, str)


class TestHistogramEmpty:
    def test_render_empty_data(self, tmp_path):
        out = histogram.render([], output_dir=str(tmp_path))
        assert Path(out.path).exists()


class TestPipelineYtCorroborateExecuteFastMode:
    def test_select_skips_unhealthy(self, monkeypatch):
        from social_research_probe.utils.core.errors import ValidationError

        cfg = MagicMock()
        cfg.service_enabled.return_value = True
        cfg.corroboration_provider = "auto"
        cfg.technology_enabled.return_value = True
        provider = MagicMock()
        provider.health_check.return_value = False
        with (
            patch("social_research_probe.config.load_active_config", return_value=cfg),
            patch(
                "social_research_probe.services.corroborating.auto_mode_providers",
                return_value=("exa", "brave"),
            ),
            patch(
                "social_research_probe.services.corroborating.get_provider",
                side_effect=[provider, ValidationError("x")],
            ),
        ):
            out = yt.YouTubeCorroborateStage()._select_corroboration_providers()
        # provider raises (not ValidationError) so loop continues, second is ValidationError
        # both fail, returns []
        assert out == []


class TestPipelineYtBuildContextSkipsNonTopN:
    def test_uses_score_top_n_fallback(self):
        from social_research_probe.platforms.state import PipelineState

        state = PipelineState(
            platform_type="youtube",
            cmd=None,
            cache=None,
            inputs={"topic": "ai"},
        )
        state.set_stage_output("corroborate", {})  # missing top_n
        state.set_stage_output("score", {"top_n": [{"id": "1"}]})
        state.set_stage_output("fetch", {"items": [], "engagement_metrics": []})
        state.set_stage_output("stats", {"stats_summary": {}})
        state.set_stage_output("charts", {"chart_outputs": []})
        ctx = yt.YouTubeSynthesisStage._build_synthesis_context(state)
        assert ctx["top_n"] == [{"id": "1"}]
