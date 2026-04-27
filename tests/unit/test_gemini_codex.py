"""Tests for technologies.llms.gemini_cli + codex_cli internals."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import MagicMock, patch

import pytest

from social_research_probe.technologies.llms import gemini_cli
from social_research_probe.technologies.llms.codex_cli import CodexRunner
from social_research_probe.technologies.llms.gemini_cli import (
    GeminiRunner,
    _extract_answer,
    _extract_citations,
    _parse_search_stdout,
    _unwrap_envelope,
    gemini_cli_available,
    gemini_search,
)
from social_research_probe.utils.core.errors import AdapterError


@pytest.fixture(autouse=True)
def _reset_avail_cache():
    gemini_cli._AVAILABILITY_CACHE = None
    yield
    gemini_cli._AVAILABILITY_CACHE = None


class TestGeminiHelpers:
    def test_unwrap_envelope_invalid(self):
        with pytest.raises(ValueError):
            _unwrap_envelope("[1,2]")

    def test_extract_answer_strips_fences(self):
        assert _extract_answer({"response": "```json\n{}\n```"}) == "{}"

    def test_extract_answer_non_string(self):
        assert _extract_answer({"response": 5}) == ""

    def test_extract_citations_grounding(self):
        envelope = {"grounding": [{"title": "T", "url": "https://x"}]}
        out = _extract_citations(envelope)
        assert out[0]["url"] == "https://x"

    def test_extract_citations_nested(self):
        envelope = {"citations": {"citations": [{"title": "T", "link": "https://y"}]}}
        out = _extract_citations(envelope)
        assert out[0]["url"] == "https://y"

    def test_extract_citations_skip_non_dict(self):
        envelope = {"sources": ["bad", {"url": "https://z"}]}
        out = _extract_citations(envelope)
        assert out[0]["url"] == "https://z"

    def test_parse_search_stdout(self):
        stdout = json.dumps({"response": "answer", "grounding": []})
        out = _parse_search_stdout(stdout)
        assert out["answer"] == "answer"


class TestGeminiAvailable:
    def test_present(self, monkeypatch):
        monkeypatch.setattr(gemini_cli.shutil, "which", lambda b: "/usr/bin/gemini")
        assert asyncio.run(gemini_cli_available()) is True

    def test_absent(self, monkeypatch):
        monkeypatch.setattr(gemini_cli.shutil, "which", lambda b: None)
        assert asyncio.run(gemini_cli_available()) is False

    def test_cached(self, monkeypatch):
        gemini_cli._AVAILABILITY_CACHE = True
        assert asyncio.run(gemini_cli_available()) is True


class TestGeminiSearch:
    def test_unavailable(self, monkeypatch):
        monkeypatch.setattr(gemini_cli.shutil, "which", lambda b: None)
        assert asyncio.run(gemini_search("q")) is None

    def test_runtime_error(self, monkeypatch):
        monkeypatch.setattr(gemini_cli.shutil, "which", lambda b: "/x")

        def boom(b, q, t):
            raise OSError

        monkeypatch.setattr(gemini_cli, "_run_search_sync", boom)
        assert asyncio.run(gemini_search("q")) is None

    def test_success(self, monkeypatch):
        monkeypatch.setattr(gemini_cli.shutil, "which", lambda b: "/x")
        monkeypatch.setattr(
            gemini_cli,
            "_run_search_sync",
            lambda b, q, t: json.dumps({"response": "a", "grounding": []}),
        )
        out = asyncio.run(gemini_search("q"))
        assert out["answer"] == "a"


class TestGeminiRunnerParse:
    def test_parse_response_invalid_envelope(self):
        with pytest.raises(AdapterError):
            GeminiRunner()._parse_response("not json")

    def test_parse_response_invalid_inner(self):
        with pytest.raises(AdapterError):
            GeminiRunner()._parse_response(json.dumps({"response": "not json"}))

    def test_parse_response_valid(self):
        out = GeminiRunner()._parse_response(json.dumps({"response": '{"a": 1}'}))
        assert out == {"a": 1}


class TestGeminiSummarizeMedia:
    def test_no_health(self, monkeypatch):
        monkeypatch.setattr(GeminiRunner, "health_check", lambda self: False)
        assert asyncio.run(GeminiRunner().summarize_media("https://x")) is None

    def test_runtime_error(self, monkeypatch):
        monkeypatch.setattr(GeminiRunner, "health_check", lambda self: True)
        cfg = MagicMock()
        cfg.llm_settings.return_value = {"binary": "gemini"}
        with (
            patch(
                "social_research_probe.technologies.llms.gemini_cli.subprocess_run",
                side_effect=OSError,
            ),
            patch("social_research_probe.technologies.llms.load_active_config", return_value=cfg),
        ):
            assert asyncio.run(GeminiRunner().summarize_media("https://x")) is None


class TestGeminiAgenticSearch:
    def test_no_search_result(self, monkeypatch):
        async def fake_search(q, *, timeout_s):
            return None

        monkeypatch.setattr(gemini_cli, "gemini_search", fake_search)
        out = asyncio.run(GeminiRunner().agentic_search("q"))
        assert out.answer == "" and out.citations == []

    def test_with_citations(self, monkeypatch):
        async def fake_search(q, *, timeout_s):
            return {"answer": "ans", "citations": [{"url": "https://x", "title": "T"}, {"url": ""}]}

        monkeypatch.setattr(gemini_cli, "gemini_search", fake_search)
        out = asyncio.run(GeminiRunner().agentic_search("q"))
        assert out.answer == "ans"
        assert len(out.citations) == 1


class TestCodex:
    def test_run_uses_temp_dir(self, monkeypatch, tmp_path):
        cfg = MagicMock()
        cfg.llm_settings.return_value = {"binary": "codex"}
        cfg.llm_timeout_seconds = 10
        result = MagicMock(stdout='{"k": 1}')
        with (
            patch("social_research_probe.technologies.llms.load_active_config", return_value=cfg),
            patch(
                "social_research_probe.technologies.llms.codex_cli.load_active_config",
                return_value=cfg,
            ),
            patch("social_research_probe.utils.io.subprocess_runner.run", return_value=result),
        ):
            out = CodexRunner().run("p", schema={"x": 1})
        assert out == {"k": 1}

    def test_run_invalid_json(self, monkeypatch):
        cfg = MagicMock()
        cfg.llm_settings.return_value = {"binary": "codex"}
        cfg.llm_timeout_seconds = 10
        result = MagicMock(stdout="not json")
        with patch("social_research_probe.technologies.llms.load_active_config", return_value=cfg):
            with patch(
                "social_research_probe.technologies.llms.codex_cli.load_active_config",
                return_value=cfg,
            ):
                with patch(
                    "social_research_probe.utils.io.subprocess_runner.run", return_value=result
                ):
                    with pytest.raises(AdapterError):
                        CodexRunner().run("p")
