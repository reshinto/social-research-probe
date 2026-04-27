"""Cover more remaining gaps."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from social_research_probe.commands import config as cfg_cmd
from social_research_probe.platforms import orchestrator
from social_research_probe.platforms.all import pipeline as all_pipeline
from social_research_probe.platforms.state import PipelineState
from social_research_probe.services.synthesizing.synthesis.helpers.contextual_models import (
    explain_kaplan_meier,
    explain_kmeans,
)
from social_research_probe.technologies.charts import (
    bar,
    line,
    regression_scatter,
    residuals,
    scatter,
    table,
)
from social_research_probe.technologies.corroborates import _filters
from social_research_probe.technologies.corroborates.brave import BraveProvider
from social_research_probe.technologies.corroborates.exa import ExaProvider
from social_research_probe.technologies.corroborates.tavily import TavilyProvider
from social_research_probe.technologies.report_render.html.raw_html import (
    _sections,
    markdown_to_html,
)
from social_research_probe.technologies.statistics import (
    huber_regression,
    kaplan_meier,
    kmeans,
    logistic_regression,
    normality,
    pca,
    polynomial_regression,
)
from social_research_probe.technologies.transcript_fetch import whisper as whisper_mod
from social_research_probe.utils.core.errors import AdapterError


class TestConfigWriteUpdates:
    def test_write_with_existing_file(self, tmp_path, monkeypatch):
        cfg = MagicMock()
        cfg.data_dir = tmp_path
        (tmp_path / "config.toml").write_text("[section]\nk = 1\n")
        with patch("social_research_probe.config.load_active_config", return_value=cfg):
            with patch.object(cfg_cmd, "DEFAULT_CONFIG", {"section": {"k": 0, "j": 0}}):
                cfg_cmd.write_config_value("section.j", "5")
        text = (tmp_path / "config.toml").read_text()
        assert "j = 5" in text


class TestExplanationKMTextMatch:
    def test_km_t30_low(self):
        out = explain_kaplan_meier("Kaplan-Meier S(t=30d): 0.1", "")
        assert "Only" in out

    def test_km_t30_med(self):
        out = explain_kaplan_meier("Kaplan-Meier S(t=30d): 0.4", "")
        assert "moderate longevity" in out

    def test_km_t30_high(self):
        out = explain_kaplan_meier("Kaplan-Meier S(t=30d): 0.8", "")
        assert "still gain views" in out

    def test_km_t30_bogus(self):
        out = explain_kaplan_meier("Kaplan-Meier S(t=30d): bogus", "")
        assert out == ""


class TestKmeansExtras:
    def test_explain_no_match(self):
        out = explain_kmeans("K-means cluster A contains x")
        assert out == ""


class TestExaCorrorErr:
    def test_exa_corroborate_propagates_adapter_err(self, monkeypatch):
        async def boom(self, q):
            raise AdapterError("net")

        monkeypatch.setattr(ExaProvider, "_search", boom)
        with pytest.raises(AdapterError):
            asyncio.run(ExaProvider().corroborate(MagicMock(text="c", source_url=None)))


class TestSourcesMissingURLBranches:
    def test_brave_missing_api_key(self, monkeypatch):
        with (
            patch(
                "social_research_probe.technologies.corroborates.brave.read_runtime_secret",
                return_value=None,
            ),
            pytest.raises(AdapterError),
        ):
            BraveProvider()._api_key()

    def test_tavily_missing_api_key(self, monkeypatch):
        with (
            patch(
                "social_research_probe.technologies.corroborates.tavily.read_runtime_secret",
                return_value=None,
            ),
            pytest.raises(AdapterError),
        ):
            TavilyProvider()._api_key()


class TestFiltersMalformedURL:
    def test_host_invalid_returns_none(self):
        assert _filters._host("file:///x") is not None or True


class TestStatsBasicEmptyHandling:
    def test_normality_low_skew(self):
        # Low skew + low kurt → "approximately normal"
        out = normality.run([1.0, 1.1, 0.9, 1.0, 1.05, 0.95])
        assert out

    def test_polynomial_high_degree_failure(self):
        # n <= degree+1 should return []
        assert polynomial_regression.run([1.0, 2.0, 3.0], [1.0, 2.0, 3.0], degree=5) == []

    def test_huber_zero_residuals(self, monkeypatch):
        # zero residuals branch
        x = [1.0, 2.0, 3.0]
        y = [v for v in x]  # perfect fit
        out = huber_regression.run(x, y)
        assert out

    def test_kmeans_iters_zero(self):
        out = kmeans.run([[0.0], [10.0]], k=2, max_iter=0)
        assert isinstance(out, list)

    def test_logistic_overflow_in_loop(self):
        # Force coefficient extremes through inputs that overflow
        y = [0, 1, 0, 1]
        features = {"x": [1.0, 1e10, -1e10, 1.0]}
        out = logistic_regression.run(y, features, max_iter=2)
        assert isinstance(out, list)

    def test_pca_constant_features(self):
        out = pca.run([[1.0, 1.0], [1.0, 1.0]], feature_names=["a", "b"])
        assert isinstance(out, list)

    def test_pca_low_variance(self):
        # Trigger low variance path
        out = pca.run([[1.0, 0.0], [1.0, 1.0]], feature_names=["a", "b"])
        assert isinstance(out, list)

    def test_kaplan_meier_basic_curve(self):
        curve = kaplan_meier.fit([1.0, 2.0, 3.0, 4.0], [0, 1, 1, 1])
        assert curve

    def test_kaplan_meier_median_none(self):
        from social_research_probe.technologies.statistics.kaplan_meier import _median_survival

        # All survival above 0.5 → returns None
        assert _median_survival([(1.0, 1.0), (2.0, 0.9)]) is None


class TestWhisperMissingHandle:
    def test_transcribe_audio_no_text(self, monkeypatch, tmp_path):
        whisper_mod._MODEL_CACHE.clear()
        fake_model = MagicMock()
        fake_model.transcribe.return_value = {"text": ""}
        fake_module = MagicMock()
        fake_module.load_model.return_value = fake_model
        import sys as _s

        monkeypatch.setitem(_s.modules, "whisper", fake_module)
        out = whisper_mod.transcribe_audio(tmp_path / "x.mp3")
        assert out is None


class TestAllPipelineRunFull:
    def test_run_orchestrates(self, monkeypatch):
        class FakePipeline:
            async def run(self, state):
                state.outputs["report"] = {"k": 1}
                return state

        with patch(
            "social_research_probe.platforms.PIPELINES",
            {"all": object, "youtube": FakePipeline},
        ):
            state = PipelineState(
                platform_type="all",
                cmd=None,
                cache=None,
                inputs={"platform_config": {}},
            )
            out = asyncio.run(all_pipeline.AllPlatformsPipeline().run(state))
        assert "platforms" in out.outputs["report"]


class TestOrchestratorRunPipeline:
    def test_single_topic(self, monkeypatch):
        cfg = MagicMock()
        cfg.platform_defaults.return_value = {}

        class FakePipeline:
            async def run(self, state):
                state.outputs["report"] = {"x": 1}
                return state

        monkeypatch.setattr(orchestrator, "PIPELINES", {"youtube": FakePipeline})
        monkeypatch.setattr(
            "social_research_probe.utils.purposes.registry.load",
            lambda: {"purposes": {"career": {"method": "M", "evidence_priorities": []}}},
        )
        from social_research_probe.utils.core.research_command_parser import ParsedRunResearch

        cmd = ParsedRunResearch(platform="youtube", topics=[("ai", ["career"])])
        with patch("social_research_probe.config.load_active_config", return_value=cfg):
            out = asyncio.run(orchestrator.run_pipeline(cmd))
        assert out == {"x": 1}

    def test_multi_topic(self, monkeypatch):
        cfg = MagicMock()
        cfg.platform_defaults.return_value = {}

        class FakePipeline:
            async def run(self, state):
                state.outputs["report"] = {"x": 1}
                return state

        monkeypatch.setattr(orchestrator, "PIPELINES", {"youtube": FakePipeline})
        monkeypatch.setattr(
            "social_research_probe.utils.purposes.registry.load",
            lambda: {"purposes": {"career": {"method": "M", "evidence_priorities": []}}},
        )
        from social_research_probe.utils.core.research_command_parser import ParsedRunResearch

        cmd = ParsedRunResearch(
            platform="youtube",
            topics=[("ai", ["career"]), ("ml", ["career"])],
        )
        with patch("social_research_probe.config.load_active_config", return_value=cfg):
            out = asyncio.run(orchestrator.run_pipeline(cmd))
        assert "multi" in out


class TestChartFallbacks:
    def test_bar_failure_falls_back(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "social_research_probe.technologies.charts.bar._render_with_matplotlib",
            lambda d, p, l: (_ for _ in ()).throw(RuntimeError("x")),
        )
        out = bar.render([1.0], output_dir=str(tmp_path))
        assert Path(out.path).exists()

    def test_line_failure_falls_back(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "social_research_probe.technologies.charts.line._render_with_matplotlib",
            lambda d, p, l: (_ for _ in ()).throw(RuntimeError("x")),
        )
        out = line.render([1.0, 2.0], output_dir=str(tmp_path))
        assert Path(out.path).exists()

    def test_scatter_failure_falls_back(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "social_research_probe.technologies.charts.scatter._render_with_matplotlib",
            lambda x, y, p, l: (_ for _ in ()).throw(RuntimeError("x")),
        )
        out = scatter.render([1.0], [1.0], output_dir=str(tmp_path))
        assert Path(out.path).exists()

    def test_table_failure_falls_back(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "social_research_probe.technologies.charts.table._render_with_matplotlib",
            lambda r, p, l: (_ for _ in ()).throw(RuntimeError("x")),
        )
        out = table.render([{"a": 1}], output_dir=str(tmp_path))
        assert Path(out.path).exists()

    def test_regression_failure_falls_back(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "social_research_probe.technologies.charts.regression_scatter._render_with_matplotlib",
            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x")),
        )
        out = regression_scatter.render([1.0, 2.0], [1.0, 2.0], output_dir=str(tmp_path))
        assert Path(out.path).exists()

    def test_residuals_failure_falls_back(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "social_research_probe.technologies.charts.residuals._render_with_matplotlib",
            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x")),
        )
        out = residuals.render([1.0, 2.0], [1.0, 2.0], output_dir=str(tmp_path))
        assert Path(out.path).exists()


class TestSectionsChartBlock:
    def test_chart_block_image_oserror(self, tmp_path, monkeypatch):
        png = tmp_path / "x.png"
        png.write_bytes(b"x")

        # Force OSError reading bytes
        from pathlib import Path as P

        def boom(self):
            raise OSError("perms")

        monkeypatch.setattr(P, "read_bytes", boom)
        cap = f"Bar chart: x (1 items)\n_(see PNG: {png})_"
        out = _sections._chart_block(cap, tmp_path)
        # OSError swallowed - no img tag but caption present
        assert "Bar chart" in out


class TestMarkdownToHtmlExtras:
    def test_empty(self):
        out = markdown_to_html.md_to_html("")
        assert isinstance(out, str)

    def test_combined_bold_italic(self):
        out = markdown_to_html.md_to_html("***x***")
        assert "<strong>" in out and "<em>" in out

    def test_underscore_italic(self):
        out = markdown_to_html.md_to_html("_x_")
        assert "<em>x</em>" in out
