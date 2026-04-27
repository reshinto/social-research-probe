"""Cover remaining small gaps for 100% ./.venv/bin/coverage."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import patch

import pytest

from social_research_probe.commands import config as cfg_cmd
from social_research_probe.commands import suggest_purposes, suggest_topics
from social_research_probe.config import load_active_config, reset_config_cache
from social_research_probe.platforms.youtube import pipeline as yt
from social_research_probe.services.enriching import transcript as transcript_svc
from social_research_probe.services.synthesizing.synthesis.helpers import formatter
from social_research_probe.services.synthesizing.synthesis.helpers.contextual_models import (
    explain_tests,
)
from social_research_probe.technologies.charts import heatmap
from social_research_probe.technologies.corroborates._filters import filter_results
from social_research_probe.technologies.media_fetch import youtube_api
from social_research_probe.technologies.statistics import (
    bayesian_linear,
    huber_regression,
    kmeans,
    naive_bayes,
    normality,
    pca,
    polynomial_regression,
)
from social_research_probe.technologies.validation.ai_slop_detector import AISlopDetector


class TestPcaInternals:
    def test_format_loadings(self):
        out = pca._format_loadings([0.5, -0.7, 0.1], ["a", "b", "c"])
        assert "b=" in out and "a=" in out

    def test_columns_empty(self):
        assert pca._columns([]) == []

    def test_variance_few(self):
        assert pca._variance([5.0], 5.0) == 0.0


class TestConfigCacheClear:
    def test_load_active_no_dir(self, monkeypatch, tmp_path):
        monkeypatch.setenv("SRP_DATA_DIR", str(tmp_path))
        reset_config_cache()
        cfg = load_active_config()
        assert cfg.data_dir == tmp_path.resolve()
        reset_config_cache()


class TestCmdConfigInvalidSection:
    def test_write_config_to_file_invalid(self, tmp_path):
        with pytest.raises(Exception):
            cfg_cmd._write_config_to_file({"a": "scalar"}, tmp_path / "x.toml")


class TestPipelineYtChartsExecuteWithFailure:
    def test_render_outputs_no_success(self, monkeypatch):
        from social_research_probe.services import ServiceResult, TechResult

        async def fake_one(self, data):
            return ServiceResult(
                service_name="charts",
                input_key="x",
                tech_results=[TechResult("t", None, None, success=False)],
            )

        monkeypatch.setattr(
            "social_research_probe.services.analyzing.charts.ChartsService.execute_one",
            fake_one,
        )
        out = asyncio.run(yt.YouTubeChartsStage._render_outputs([{"x": 1}]))
        assert out == []


class TestYoutubeApiSearch:
    def test_search_youtube_no_cache(self, monkeypatch, tmp_path):
        monkeypatch.setenv("SRP_DATA_DIR", str(tmp_path))
        with (
            patch.object(youtube_api, "get_json", return_value=None),
            patch.object(youtube_api, "set_json"),
            patch.object(youtube_api, "_search_videos", return_value=[{"id": "v"}]),
            patch.object(youtube_api, "resolve_youtube_api_key", return_value="k"),
        ):
            out = youtube_api.search_youtube("topic", max_items=5)
        assert out == [{"id": "v"}]


class TestStatsTinyBranches:
    def test_huber_weight_within(self):
        assert huber_regression._huber_weight(0.5, 1.345) == 1.0

    def test_huber_weight_outside(self):
        assert huber_regression._huber_weight(2.0, 1.345) < 1.0

    def test_normality_classify_non_normal(self):
        assert normality._classify(2.0, 5.0) == "non-normal — prefer nonparametric tests"

    def test_normality_classify_normal(self):
        assert normality._classify(0.1, 0.1) == "approximately normal"

    def test_polynomial_fit_coefficients_singular(self):
        assert polynomial_regression.fit_coefficients([1.0] * 3, [1.0] * 3, degree=10) is None

    def test_kmeans_recompute_empty_cluster(self):
        out = kmeans._recompute_centroids([[1.0]], [0], k=2, prev=[[5.0], [10.0]])
        assert out[1] == [10.0]

    def test_naive_bayes_single_value(self):
        _priors, _mus, sigmas = naive_bayes.fit(["a", "a"], {"x": [1.0, 1.0]})
        assert sigmas["a"]["x"] >= 1e-6

    def test_bayesian_diag_inverse_singular(self):
        out = bayesian_linear._diagonal_of_inverse([[0.0, 0.0], [0.0, 0.0]], 2)
        assert out is None


class TestExplainTestsNormality:
    def test_non_normal_metric(self):
        out = explain_tests("Normality check x: non-normal", "")
        assert "median" in out

    def test_non_normal_finding(self):
        out = explain_tests("Normality check x", "non-normal verdict")
        assert "median" in out


class TestFiltersBlankUrl:
    def test_filter_keeps_blank_url(self):
        kept, _, _ = filter_results([{"url": ""}, {"url": None}], None)
        assert len(kept) == 2


class TestHeatmapWithFeatures:
    def test_render_with_failure(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            heatmap,
            "_render_with_matplotlib",
            lambda n, m, p, l: (_ for _ in ()).throw(RuntimeError("x")),
        )
        out = heatmap.render({"a": [1.0, 2.0], "b": [3.0, 4.0]}, output_dir=str(tmp_path))
        assert Path(out.path).exists()


class TestSuggestExtras:
    def test_suggest_topics_call_llm(self, monkeypatch):
        monkeypatch.setattr(
            "social_research_probe.services.llm.registry.run_with_fallback",
            lambda p, s, r: {"suggestions": []},
        )
        out = suggest_topics._call_llm("p", "claude")
        assert out["suggestions"] == []

    def test_suggest_purposes_call_llm(self, monkeypatch):
        monkeypatch.setattr(
            "social_research_probe.services.llm.registry.run_with_fallback",
            lambda p, s, r: {"suggestions": []},
        )
        out = suggest_purposes._call_llm("p", "claude")
        assert out["suggestions"] == []


class TestAiSlopExecute:
    def test_execute_returns_score(self):
        out = asyncio.run(AISlopDetector()._execute("Some text content."))
        assert 0.0 <= out <= 1.0


class TestTranscriptServiceWhisperFallbackRuns:
    def test_whisper_fallback_path(self, monkeypatch):
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
        out = asyncio.run(transcript_svc.TranscriptService().execute_one({"url": "u"}))
        assert any(r.tech_name == "whisper_fallback" for r in out.tech_results)


class TestFormatterEnsureSentence:
    def test_blank(self):
        assert formatter._ensure_sentence("") == ""

    def test_already_punct(self):
        assert formatter._ensure_sentence("hello.") == "hello."

    def test_appends(self):
        assert formatter._ensure_sentence("hello") == "hello."


class TestResearchExecutePipeline:
    def test_executes(self, monkeypatch):
        from social_research_probe.commands import research

        async def fake_run(cmd):
            return {"report_path": "/x"}

        monkeypatch.setattr("social_research_probe.platforms.orchestrator.run_pipeline", fake_run)
        out = research._execute_research_pipeline("youtube", "ai", ("career",))
        assert out["report_path"] == "/x"
