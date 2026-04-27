"""Bulk tests for remaining gaps: ensemble, base, voicebox, youtube_api, writer, cli/handlers, all_pipeline."""

from __future__ import annotations

import asyncio
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

import social_research_probe.services.reporting as writer
from social_research_probe.cli import handlers
from social_research_probe.commands import Command
from social_research_probe.platforms.all import pipeline as all_pipeline
from social_research_probe.platforms.state import PipelineState
from social_research_probe.services.llm import ensemble
from social_research_probe.technologies import base as tech_base
from social_research_probe.technologies.media_fetch import youtube_api
from social_research_probe.technologies.tts import voicebox
from social_research_probe.utils.core.errors import AdapterError


class TestEnsembleProvider:
    def test_unknown_runner_returns_none(self):
        assert asyncio.run(ensemble._run_provider("?", "p")) is None


class TestEnsembleSynthesize:
    def test_synthesize_chains_to_provider(self, monkeypatch):
        called = {}

        async def fake_run(name, prompt, task="synthesising ensemble responses"):
            called[name] = called.get(name, 0) + 1
            return "out"

        monkeypatch.setattr(ensemble, "_run_provider", fake_run)
        cfg = MagicMock()
        cfg.service_enabled.return_value = True
        cfg.technology_enabled.return_value = True
        out = asyncio.run(ensemble._synthesize({"a": "x", "b": "y"}, "orig", cfg))
        assert out == "out"

    def test_synthesize_falls_back_to_best(self, monkeypatch):
        async def fake_run(name, prompt, task="synthesising ensemble responses"):
            return None

        monkeypatch.setattr(ensemble, "_run_provider", fake_run)
        cfg = MagicMock()
        cfg.service_enabled.return_value = True
        cfg.technology_enabled.return_value = True
        out = asyncio.run(ensemble._synthesize({"claude": "ans"}, "orig", cfg))
        assert out == "ans"


class TestEnsembleMulti:
    def test_preferred_succeeds(self, monkeypatch):
        cfg = MagicMock()
        cfg.service_enabled.return_value = True
        cfg.llm_runner = "claude"
        cfg.preferred_free_text_runner = "claude"
        cfg.technology_enabled.return_value = True

        async def fake_run(name, prompt, task="generating response"):
            return "preferred-answer" if name == "claude" else None

        monkeypatch.setattr(ensemble, "_run_provider", fake_run)
        with patch.object(ensemble, "load_active_config", return_value=cfg):
            out = asyncio.run(ensemble.multi_llm_prompt("p"))
        assert out == "preferred-answer"

    def test_no_preferred_uses_ensemble(self, monkeypatch):
        cfg = MagicMock()
        cfg.service_enabled.return_value = True
        cfg.llm_runner = "claude"
        cfg.preferred_free_text_runner = None
        cfg.technology_enabled.return_value = True

        async def fake_run(name, prompt, task="generating response"):
            return "x"

        monkeypatch.setattr(ensemble, "_run_provider", fake_run)
        with patch.object(ensemble, "load_active_config", return_value=cfg):
            out = asyncio.run(ensemble.multi_llm_prompt("p"))
        assert out == "x"


class _NopTech(tech_base.BaseTechnology):
    name = "nop"
    health_check_key = "nop"
    enabled_config_key = "nop"

    async def _execute(self, data):
        return f"nop:{data}"


class _BoomTech(tech_base.BaseTechnology):
    name = "boom"
    health_check_key = "boom"
    enabled_config_key = "boom"

    async def _execute(self, data):
        raise RuntimeError("boom")


class TestTechBase:
    def test_disabled_returns_none(self):
        cfg = MagicMock()
        cfg.technology_enabled.return_value = False
        with patch("social_research_probe.technologies.base.load_active_config", return_value=cfg):
            assert asyncio.run(_NopTech().execute("d")) is None

    def test_enabled_runs(self):
        cfg = MagicMock()
        cfg.technology_enabled.return_value = True
        cfg.debug_enabled.return_value = False
        with patch("social_research_probe.technologies.base.load_active_config", return_value=cfg):
            assert asyncio.run(_NopTech().execute("d")) == "nop:d"

    def test_exception_returns_none(self):
        cfg = MagicMock()
        cfg.technology_enabled.return_value = True
        cfg.debug_enabled.return_value = False
        with patch("social_research_probe.technologies.base.load_active_config", return_value=cfg):
            assert asyncio.run(_BoomTech().execute("d")) is None

    def test_debug_logs_enabled(self):
        cfg = MagicMock()
        cfg.technology_enabled.return_value = True
        cfg.debug_enabled.return_value = True
        with patch("social_research_probe.technologies.base.load_active_config", return_value=cfg):
            assert asyncio.run(_NopTech().execute("d")) == "nop:d"

    def test_health_check_default(self):
        out = asyncio.run(_NopTech().health_check())
        assert out.healthy is True
        assert out.key == "nop"

    def test_cache_key(self):
        assert len(_NopTech()._cache_key("d")) == 64


class TestVoicebox:
    def test_synthesize_http_error(self, monkeypatch):
        class FakeHTTP(urllib.error.HTTPError):
            def __init__(self):
                super().__init__("u", 500, "err", {}, None)

            def read(self):
                return b"detail"

        def boom(*a, **kw):
            raise FakeHTTP()

        monkeypatch.setattr(voicebox.urllib.request, "urlopen", boom)
        with pytest.raises(RuntimeError):
            voicebox.synthesize("text", api_base="http://x", profile_id="p")

    def test_synthesize_url_error(self, monkeypatch):
        def boom(*a, **kw):
            raise urllib.error.URLError("connect refused")

        monkeypatch.setattr(voicebox.urllib.request, "urlopen", boom)
        with pytest.raises(RuntimeError, match="unreachable"):
            voicebox.synthesize("text", api_base="http://x", profile_id="p")

    def test_synthesize_empty(self, monkeypatch):
        class FakeResp:
            headers = {"Content-Type": "audio/wav"}

            def read(self):
                return b""

            def __enter__(self):
                return self

            def __exit__(self, *a):
                pass

        monkeypatch.setattr(voicebox.urllib.request, "urlopen", lambda *a, **kw: FakeResp())
        with pytest.raises(RuntimeError, match="empty"):
            voicebox.synthesize("text", api_base="http://x", profile_id="p")

    def test_synthesize_success_and_write(self, monkeypatch, tmp_path):
        class FakeResp:
            headers = {"Content-Type": "audio/wav"}

            def read(self):
                return b"audio"

            def __enter__(self):
                return self

            def __exit__(self, *a):
                pass

        monkeypatch.setattr(voicebox.urllib.request, "urlopen", lambda *a, **kw: FakeResp())
        out = voicebox.write_audio(
            "text", out_base=tmp_path / "audio", api_base="http://x", profile_id="p"
        )
        assert out.exists() and out.suffix == ".wav"

    def test_get_server_url_from_secret(self, monkeypatch):
        with patch(
            "social_research_probe.technologies.tts.voicebox.read_runtime_secret",
            return_value="http://secret",
        ):
            assert voicebox._get_server_url() == "http://secret"

    def test_get_server_url_from_config(self, monkeypatch):
        with patch(
            "social_research_probe.technologies.tts.voicebox.read_runtime_secret",
            return_value=None,
        ):
            cfg = MagicMock()
            cfg.voicebox = {"api_base": "http://cfg"}
            with patch("social_research_probe.config.load_active_config", return_value=cfg):
                assert voicebox._get_server_url() == "http://cfg"


class TestYouTubeApi:
    def test_resolve_api_key_from_secret(self, monkeypatch):
        monkeypatch.delenv("SRP_YOUTUBE_API_KEY", raising=False)
        with patch("social_research_probe.commands.config.read_secret", return_value="seck"):
            assert youtube_api.resolve_youtube_api_key() == "seck"

    def test_youtube_health_check(self, monkeypatch):
        monkeypatch.setenv("SRP_YOUTUBE_API_KEY", "x")
        assert youtube_api.youtube_health_check() is True

    def test_search_youtube_cached(self, monkeypatch, tmp_path):
        monkeypatch.setenv("SRP_DATA_DIR", str(tmp_path))
        monkeypatch.delenv("SRP_DISABLE_CACHE", raising=False)
        with patch.object(youtube_api, "get_json", return_value={"items": [{"a": 1}]}):
            with patch.object(youtube_api, "set_json"):
                out = youtube_api.search_youtube("topic", max_items=5)
        assert out == [{"a": 1}]

    def test_search_youtube_cached_invalid(self, monkeypatch, tmp_path):
        monkeypatch.setenv("SRP_DATA_DIR", str(tmp_path))
        with patch.object(youtube_api, "get_json", return_value={"items": "bad"}):
            out = youtube_api.search_youtube("topic", max_items=5)
        assert out == []

    def test_search_videos_failure(self, monkeypatch):
        with patch.object(youtube_api, "_build_client") as bc:
            bc.return_value.search.return_value.list.return_value.execute.side_effect = (
                RuntimeError("api")
            )
            with pytest.raises(AdapterError):
                youtube_api._search_videos("k", topic="t", max_items=5, published_after=None)

    def test_fetch_video_details_failure(self, monkeypatch):
        with patch.object(youtube_api, "_build_client") as bc:
            bc.return_value.videos.return_value.list.return_value.execute.side_effect = (
                RuntimeError("api")
            )
            with pytest.raises(AdapterError):
                youtube_api._fetch_video_details("k", video_ids=["v"])

    def test_fetch_channel_details_failure(self, monkeypatch):
        with patch.object(youtube_api, "_build_client") as bc:
            bc.return_value.channels.return_value.list.return_value.execute.side_effect = (
                RuntimeError("api")
            )
            with pytest.raises(AdapterError):
                youtube_api._fetch_channel_details("k", channel_ids=["c"])

    def test_hydrate_youtube_cached(self, monkeypatch, tmp_path):
        monkeypatch.setenv("SRP_DATA_DIR", str(tmp_path))
        with patch.object(youtube_api, "get_json", return_value={"videos": [{}], "channels": [{}]}):
            v, c = asyncio.run(youtube_api.hydrate_youtube(["v1"], ["c1"]))
        assert v == [{}] and c == [{}]


class TestReportingWriter:
    def test_write_md_when_html_disabled(self, tmp_path, monkeypatch):
        monkeypatch.setattr(writer, "stage_flag", lambda *a, **k: False)
        cfg = MagicMock()
        cfg.data_dir = tmp_path
        with patch("social_research_probe.config.load_active_config", return_value=cfg):
            out = writer.write_final_report(
                {
                    "items_top_n": [],
                    "topic": "t",
                    "platform": "p",
                    "purpose_set": [],
                    "stats_summary": {},
                    "platform_engagement_summary": "",
                    "evidence_summary": "",
                    "chart_captions": [],
                    "warnings": [],
                },
                allow_html=False,
            )
        assert out.endswith("report.md")

    def test_html_disabled_via_multi(self, tmp_path, monkeypatch):
        monkeypatch.setattr(writer, "stage_flag", lambda *a, **k: True)
        monkeypatch.setattr(writer, "service_flag", lambda *a, **k: True)
        cfg = MagicMock()
        cfg.data_dir = tmp_path
        with patch("social_research_probe.config.load_active_config", return_value=cfg):
            out = writer.write_final_report({"multi": []}, allow_html=True)
        assert out.endswith("report.md")

    def test_html_failure_falls_back(self, tmp_path, monkeypatch):
        monkeypatch.setattr(writer, "stage_flag", lambda *a, **k: True)
        monkeypatch.setattr(writer, "service_flag", lambda *a, **k: True)
        cfg = MagicMock()
        cfg.data_dir = tmp_path
        with patch("social_research_probe.config.load_active_config", return_value=cfg):
            with patch.object(writer, "write_html_report", side_effect=RuntimeError):
                out = writer.write_final_report(
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
        assert out.endswith("report.md")

    def test_html_success(self, tmp_path, monkeypatch):
        monkeypatch.setattr(writer, "stage_flag", lambda *a, **k: True)
        monkeypatch.setattr(writer, "service_flag", lambda *a, **k: True)
        cfg = MagicMock()
        cfg.data_dir = tmp_path
        target = tmp_path / "x.html"
        target.write_text("html")
        with patch("social_research_probe.config.load_active_config", return_value=cfg):
            with patch.object(writer, "write_html_report", return_value=target):
                with patch.object(writer, "serve_report_command", return_value="cmd"):
                    out = writer.write_final_report(
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


class TestCliHandlers:
    def test_handlers_factory_full(self):
        h = handlers.handlers_factory()
        assert all(
            cmd in h
            for cmd in (
                Command.UPDATE_TOPICS,
                Command.UPDATE_PURPOSES,
                Command.SHOW_TOPICS,
                Command.SHOW_PURPOSES,
                Command.SUGGEST_TOPICS,
                Command.SUGGEST_PURPOSES,
                Command.SHOW_PENDING,
                Command.APPLY_PENDING,
                Command.DISCARD_PENDING,
                Command.STAGE_SUGGESTIONS,
                Command.RESEARCH,
                Command.CORROBORATE_CLAIMS,
                Command.RENDER,
                Command.INSTALL_SKILL,
                Command.SETUP,
                Command.REPORT,
                Command.SERVE_REPORT,
                Command.CONFIG,
            )
        )

    def test_dispatch_config(self):
        with patch("social_research_probe.commands.config.run", return_value=0) as mock:
            assert handlers._dispatch_config(MagicMock()) == 0
        mock.assert_called_once()


class TestAllPipeline:
    def test_construct(self):
        all_pipeline.AllPlatformsPipeline()  # type: ignore[call-arg]

    def test_run_one(self):
        class FakePipeline:
            async def run(self, state):
                state.outputs["report"] = {"x": 1}
                return state

        async def coro():
            state = PipelineState(
                platform_type="x",
                cmd=None,
                cache=None,
                inputs={"platform_config": {}},
            )
            return await all_pipeline._run_one("youtube", FakePipeline, state)

        with patch(
            "social_research_probe.platforms.registry.get_client",
            return_value=MagicMock(),
        ):
            name, out = asyncio.run(coro())
        assert name == "youtube" and out == {"x": 1}
