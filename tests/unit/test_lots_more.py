"""Cover lots of small remaining gaps."""

from __future__ import annotations

import argparse
import asyncio
import getpass
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from social_research_probe.commands import ConfigSubcommand
from social_research_probe.commands import config as cfg_cmd
from social_research_probe.commands import report as report_cmd
from social_research_probe.config import _active_data_dir
from social_research_probe.platforms import (
    BaseResearchPlatform,
    BaseStage,
    run_stages,
)
from social_research_probe.platforms.state import PipelineState
from social_research_probe.platforms.youtube import pipeline as yt
from social_research_probe.services.analyzing import charts as charts_svc
from social_research_probe.services.synthesizing.synthesis.helpers.contextual_models import (
    explain_kaplan_meier,
)
from social_research_probe.technologies.charts import histogram
from social_research_probe.technologies.corroborates.brave import BraveProvider
from social_research_probe.technologies.corroborates.exa import ExaProvider
from social_research_probe.technologies.corroborates.tavily import TavilyProvider
from social_research_probe.technologies.media_fetch import youtube_api, yt_dlp
from social_research_probe.technologies.statistics import (
    huber_regression,
    kmeans,
    logistic_regression,
    normality,
    pca,
    polynomial_regression,
)
from social_research_probe.technologies.tts import mac_tts, voicebox


class TestConfigCmd:
    def test_run_set_writes(self, tmp_path, monkeypatch):
        cfg = MagicMock()
        cfg.data_dir = tmp_path
        with patch("social_research_probe.config.load_active_config", return_value=cfg):
            with patch.object(cfg_cmd, "DEFAULT_CONFIG", {"section": {"k": 0}}):
                ns = argparse.Namespace(
                    config_cmd=ConfigSubcommand.SET, key="section.k", value="42"
                )
                assert cfg_cmd.run(ns) == 0

    def test_run_set_secret_via_run(self, tmp_path):
        cfg = MagicMock()
        cfg.data_dir = tmp_path
        with patch("social_research_probe.config.load_active_config", return_value=cfg):
            with patch.object(getpass, "getpass", return_value="value"):
                ns = argparse.Namespace(
                    config_cmd=ConfigSubcommand.SET_SECRET,
                    name="x",
                    from_stdin=False,
                )
                assert cfg_cmd.run(ns) == 0


class TestActiveDataDir:
    def test_env(self, monkeypatch, tmp_path):
        monkeypatch.setenv("SRP_DATA_DIR", str(tmp_path))
        out = _active_data_dir()
        assert out == tmp_path.resolve()

    def test_no_env(self, monkeypatch):
        monkeypatch.delenv("SRP_DATA_DIR", raising=False)
        out = _active_data_dir()
        assert out == (Path.home() / ".social-research-probe").resolve()


class TestExplainKMNotReached:
    def test_not_reached_metric(self):
        out = explain_kaplan_meier("Kaplan-Meier median survival: not reached", "")
        assert "durable" in out

    def test_not_reached_finding(self):
        out = explain_kaplan_meier("Kaplan-Meier median survival days", "not reached")
        assert "durable" in out

    def test_no_match(self):
        out = explain_kaplan_meier("Kaplan-Meier median survival x", "")
        assert out == ""


class TestCorroborateProviders:
    def test_exa_search_failure(self, monkeypatch):
        async def boom(self):
            raise Exception("oops")

        async def fake_post(*a, **kw):
            raise Exception("net")

        # Force HTTPError path via httpx
        from social_research_probe.utils.core.errors import AdapterError

        async def fake_search(self, query):
            raise AdapterError("x")

        monkeypatch.setattr(ExaProvider, "_search", fake_search)
        # Already covered in tests; here we test corroborate raises through
        with pytest.raises(AdapterError):
            asyncio.run(ExaProvider().corroborate(MagicMock(text="c", source_url=None)))

    def test_brave_corroborate_runs(self, monkeypatch):
        async def fake(self, q):
            return [{"url": "https://x"}]

        monkeypatch.setattr(BraveProvider, "_search", fake)
        out = asyncio.run(BraveProvider().corroborate(MagicMock(text="c", source_url=None)))
        assert out.verdict == "supported"

    def test_tavily_corroborate_runs(self, monkeypatch):
        async def fake(self, q):
            return [{"url": "https://x"}]

        monkeypatch.setattr(TavilyProvider, "_search", fake)
        out = asyncio.run(TavilyProvider().corroborate(MagicMock(text="c", source_url=None)))
        assert out.verdict == "supported"


class TestYoutubeApiHydrate:
    def test_hydrate_no_cache(self, monkeypatch, tmp_path):
        monkeypatch.setenv("SRP_DATA_DIR", str(tmp_path))
        monkeypatch.delenv("SRP_DISABLE_CACHE", raising=False)
        with patch.object(youtube_api, "get_json", return_value=None):
            with patch.object(youtube_api, "set_json"):
                with patch.object(youtube_api, "resolve_youtube_api_key", return_value="k"):
                    with patch.object(
                        youtube_api, "_fetch_video_details", return_value=[{"id": "v"}]
                    ):
                        with patch.object(
                            youtube_api, "_fetch_channel_details", return_value=[{"id": "c"}]
                        ):
                            v, _c = asyncio.run(youtube_api.hydrate_youtube(["v"], ["c"]))
        assert v == [{"id": "v"}]


class TestYtDlpExecute:
    def test_failure_raises(self, monkeypatch):
        monkeypatch.setattr(yt_dlp, "download_audio", lambda url, tmp: None)
        with pytest.raises(RuntimeError):
            asyncio.run(yt_dlp.YtDlpFetch()._execute("u"))

    def test_success(self, monkeypatch):
        def fake_dl(url, tmp):
            p = Path(tmp) / "audio.mp3"
            p.write_bytes(b"audio")
            return p

        monkeypatch.setattr(yt_dlp, "download_audio", fake_dl)
        out = asyncio.run(yt_dlp.YtDlpFetch()._execute("u"))
        assert out.exists()


class TestVoiceboxExecute:
    def test_execute_basic(self, monkeypatch, tmp_path):
        out_path = tmp_path / "audio.wav"
        out_path.write_bytes(b"x")

        def fake_write_audio(text, *, out_base, api_base, profile_id):
            return out_path

        with patch.object(voicebox, "_get_server_url", return_value="http://x"):
            with patch.object(voicebox, "_get_default_profile", return_value="P"):
                with patch.object(voicebox, "write_audio", fake_write_audio):
                    out = asyncio.run(voicebox.VoiceboxTTS()._execute("text"))
        assert out["profile"] == "P"


class TestMacTtsExecute:
    def test_execute(self, monkeypatch, tmp_path):
        called = {}

        def fake_synth(text, voice, out_path):
            called["voice"] = voice
            out_path.write_text("x")

        monkeypatch.setattr(mac_tts, "synthesize_mac", fake_synth)
        from types import SimpleNamespace

        cfg = SimpleNamespace(tunables={"tts": {"mac": {"voice": "Vicki"}}})
        with patch.object(mac_tts, "load_active_config", return_value=cfg):
            out = asyncio.run(mac_tts.MacTTS()._execute("hello"))
        assert called["voice"] == "Vicki"
        assert out.exists()

    def test_execute_default_voice(self, monkeypatch):
        captured = {}

        def fake_synth(text, voice, out_path):
            captured["voice"] = voice
            out_path.write_text("x")

        monkeypatch.setattr(mac_tts, "synthesize_mac", fake_synth)
        cfg = MagicMock()
        # Make .tunables.get raise to fall back to default
        cfg.tunables.get.side_effect = TypeError("nope")
        with patch.object(mac_tts, "load_active_config", return_value=cfg):
            out = asyncio.run(mac_tts.MacTTS()._execute("hello"))
        assert captured["voice"] == "Alex"
        assert out.exists()


class TestPlatformsBase:
    def test_run_stages(self, monkeypatch):
        captured = []

        class StageA(BaseStage):
            def stage_name(self):
                return "a"

            def _is_enabled(self, state):
                return True

            async def execute(self, state):
                captured.append("a")
                return state

        class StageB(BaseStage):
            def stage_name(self):
                return "b"

            def _is_enabled(self, state):
                return False

            async def execute(self, state):
                captured.append("b")
                return state

        class P(BaseResearchPlatform):
            def stages(self):
                return [StageA(), StageB()]

            async def run(self, state):
                return state

        state = PipelineState(platform_type="x", cmd=None, cache=None)
        asyncio.run(run_stages(P(), state))
        assert captured == ["a"]


class TestStatsExtras:
    def test_normality_too_few(self):
        assert normality.run([1.0]) == []

    def test_polynomial_too_short(self):
        assert polynomial_regression.run([1.0, 2.0], [1.0, 2.0], degree=2) == []

    def test_polynomial_singular(self):
        # Force singular fit: all x identical
        out = polynomial_regression.run([1.0] * 5, [2.0] * 5, degree=2)
        assert isinstance(out, list)

    def test_huber_basic(self):
        x = list(range(1, 8))
        y = [v + 0.1 for v in x]
        out = huber_regression.run(x, y)
        assert out

    def test_kmeans_fit_zero(self):
        # k=1 returns empty
        out = kmeans.run([[1.0], [2.0]], k=1)
        assert out == []

    def test_logistic_overflow(self):
        # Force sigmoid clamp via huge value
        assert logistic_regression._sigmoid(1000) == 1.0
        assert logistic_regression._sigmoid(-1000) == 0.0

    def test_pca_dot(self):
        assert pca._dot([1.0, 2.0], [3.0, 4.0]) == 11.0


class TestHistogramRender:
    def test_render_with_failure_falls_back(self, tmp_path, monkeypatch):
        def boom(data, path, label, bins):
            raise RuntimeError("x")

        monkeypatch.setattr(histogram, "_render_with_matplotlib", boom)
        result = histogram.render([1.0, 2.0], output_dir=str(tmp_path))
        assert Path(result.path).exists()


class TestChartsServiceFailures:
    def test_render_failure(self, monkeypatch):
        async def boom(items, charts_dir):
            raise RuntimeError("nope")

        monkeypatch.setattr(
            charts_svc.ChartsService,
            "_render_with_cache",
            classmethod(lambda cls, i, d: boom(i, d)),
        )
        cfg = MagicMock()
        cfg.data_dir = Path("/tmp/test-charts-failures")
        with patch("social_research_probe.config.load_active_config", return_value=cfg):
            out = asyncio.run(charts_svc.ChartsService().execute_one({"scored_items": [{"x": 1}]}))
        assert out.tech_results[0].success is False


class TestReportCmdHTMLOut:
    def test_run_writes_html(self, tmp_path, monkeypatch, capsys):
        path = tmp_path / "r.json"
        path.write_text(json.dumps({"platform": "youtube"}))
        cfg = MagicMock()
        cfg.stage_enabled.return_value = True
        cfg.service_enabled.return_value = True
        cfg.technology_enabled.return_value = False

        out_html = tmp_path / "out.html"
        monkeypatch.setattr(
            "social_research_probe.technologies.report_render.html.raw_html.youtube.render_html",
            lambda *a, **kw: "<html/>",
        )
        monkeypatch.setattr(
            "social_research_probe.technologies.report_render.html.raw_html.youtube.serve_report_command",
            lambda p: "cmd",
        )
        monkeypatch.setattr(
            "social_research_probe.technologies.report_render.html.raw_html.youtube._technology_logs_enabled",
            lambda: False,
        )
        monkeypatch.setattr(
            "social_research_probe.technologies.report_render.html.raw_html.youtube._voicebox_api_base",
            lambda: "http://x",
        )
        with patch("social_research_probe.commands.report.load_active_config", return_value=cfg):
            rc = report_cmd.run(str(path), None, None, None, str(out_html))
        assert rc == 0
        assert out_html.read_text() == "<html/>"


class TestPipelineYtAssembleDisabled:
    def test_assemble_disabled_returns_state(self, monkeypatch):
        cfg = MagicMock()
        cfg.stage_enabled.return_value = False
        with patch("social_research_probe.config.load_active_config", return_value=cfg):
            state = PipelineState(
                platform_type="youtube",
                cmd=None,
                cache=None,
                inputs={"topic": "ai", "purpose_names": []},
            )
            out = asyncio.run(yt.YouTubeAssembleStage().execute(state))
        assert out is state
