"""Cover exa/brave/tavily _search HTTP paths and report TTS branch."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import httpx
import pytest

from social_research_probe.technologies.corroborates.brave import BraveProvider
from social_research_probe.technologies.corroborates.exa import ExaProvider
from social_research_probe.technologies.corroborates.tavily import TavilyProvider
from social_research_probe.utils.core.errors import AdapterError


class FakeResponse:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("err", request=None, response=None)

    def json(self):
        return self._payload


class FakeAsyncClient:
    def __init__(self, response):
        self._response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        pass

    async def post(self, *a, **kw):
        return self._response

    async def get(self, *a, **kw):
        return self._response


def _patch_httpx(monkeypatch, response):
    def factory(*a, **kw):
        return FakeAsyncClient(response)

    monkeypatch.setattr(httpx, "AsyncClient", factory)


class TestExaSearch:
    def test_success(self, monkeypatch):
        with patch.object(ExaProvider, "_api_key", return_value="k"):
            _patch_httpx(monkeypatch, FakeResponse({"results": [{"url": "https://a"}]}))
            out = asyncio.run(ExaProvider()._search("q"))
        assert out == [{"url": "https://a"}]

    def test_http_error(self, monkeypatch):
        with patch.object(ExaProvider, "_api_key", return_value="k"):
            err_resp = FakeResponse({}, status=500)
            _patch_httpx(monkeypatch, err_resp)
            with pytest.raises(AdapterError):
                asyncio.run(ExaProvider()._search("q"))

    def test_missing_results_key(self, monkeypatch):
        with patch.object(ExaProvider, "_api_key", return_value="k"):
            _patch_httpx(monkeypatch, FakeResponse({"other": []}))
            with pytest.raises(AdapterError):
                asyncio.run(ExaProvider()._search("q"))


class TestBraveSearch:
    def test_success(self, monkeypatch):
        with patch.object(BraveProvider, "_api_key", return_value="k"):
            _patch_httpx(monkeypatch, FakeResponse({"web": {"results": [{"url": "https://a"}]}}))
            out = asyncio.run(BraveProvider()._search("q"))
        assert out == [{"url": "https://a"}]

    def test_http_error(self, monkeypatch):
        with patch.object(BraveProvider, "_api_key", return_value="k"):
            _patch_httpx(monkeypatch, FakeResponse({}, status=500))
            with pytest.raises(AdapterError):
                asyncio.run(BraveProvider()._search("q"))

    def test_no_web_key(self, monkeypatch):
        with patch.object(BraveProvider, "_api_key", return_value="k"):
            _patch_httpx(monkeypatch, FakeResponse({}))
            out = asyncio.run(BraveProvider()._search("q"))
        assert out == []


class TestTavilySearch:
    def test_success(self, monkeypatch):
        with patch.object(TavilyProvider, "_api_key", return_value="k"):
            _patch_httpx(monkeypatch, FakeResponse({"results": [{"url": "https://a"}]}))
            out = asyncio.run(TavilyProvider()._search("q"))
        assert out == [{"url": "https://a"}]

    def test_http_error(self, monkeypatch):
        with patch.object(TavilyProvider, "_api_key", return_value="k"):
            _patch_httpx(monkeypatch, FakeResponse({}, status=500))
            with pytest.raises(AdapterError):
                asyncio.run(TavilyProvider()._search("q"))


class TestReportPrepareTts:
    def test_prepare_tts_with_voicebox_disabled(self, monkeypatch, tmp_path):
        from social_research_probe.commands import report as report_cmd

        cfg = MagicMock()
        cfg.technology_enabled.return_value = False
        with patch.object(report_cmd, "load_active_config", return_value=cfg):
            profiles, name, sources = report_cmd._prepare_tts_setup({}, None, False)
        assert profiles == [] and name is None and sources == {}

    def test_prepare_tts_with_voicebox_enabled(self, monkeypatch, tmp_path):
        from social_research_probe.commands import report as report_cmd

        cfg = MagicMock()
        cfg.technology_enabled.return_value = True
        monkeypatch.setattr(
            "social_research_probe.technologies.report_render.html.raw_html.youtube._fetch_voicebox_profiles",
            lambda b: [{"id": "1", "name": "A"}],
        )
        monkeypatch.setattr(
            "social_research_probe.technologies.report_render.html.raw_html.youtube._write_discovered_voicebox_profile_names",
            lambda p: None,
        )
        monkeypatch.setattr(
            "social_research_probe.technologies.report_render.html.raw_html.youtube._voicebox_api_base",
            lambda: "http://x",
        )
        monkeypatch.setattr(
            "social_research_probe.technologies.report_render.html.raw_html.youtube._voicebox_default_profile_name",
            lambda: "A",
        )
        monkeypatch.setattr(
            "social_research_probe.technologies.report_render.html.raw_html.youtube._select_voicebox_profile",
            lambda profiles, **kw: profiles[0],
        )
        monkeypatch.setattr(
            "social_research_probe.technologies.report_render.html.raw_html.youtube._audio_report_enabled",
            lambda: True,
        )
        monkeypatch.setattr(
            "social_research_probe.technologies.report_render.html.raw_html.youtube._prepare_voiceover_audios",
            lambda *a, **kw: {"A": "audio.wav"},
        )
        with patch.object(report_cmd, "load_active_config", return_value=cfg):
            _profiles, name, sources = report_cmd._prepare_tts_setup(
                {}, str(tmp_path / "out.html"), False
            )
        assert name == "A" and sources["A"] == "audio.wav"
