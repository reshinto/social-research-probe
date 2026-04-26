"""Tests for tech.llms package."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from social_research_probe.technologies.llms import (
    AgenticSearchCitation,
    AgenticSearchResult,
    CapabilityUnavailableError,
    LLMRunner,
)
from social_research_probe.technologies.llms.claude_cli import (
    ClaudeRunner,
    _parse_claude_search_body,
)
from social_research_probe.technologies.llms.codex_cli import CodexRunner
from social_research_probe.technologies.llms.gemini_cli import GeminiRunner
from social_research_probe.utils.core.errors import AdapterError


def test_capability_unavailable_is_runtime_error():
    assert issubclass(CapabilityUnavailableError, RuntimeError)


def test_llm_runner_is_abstract():
    with pytest.raises(TypeError):
        LLMRunner()  # type: ignore[abstract]


def test_default_summarize_media_returns_none():
    class Stub(LLMRunner):
        name = "stub"

        def health_check(self):
            return True

        def run(self, prompt, *, schema=None):
            return {}

    out = asyncio.run(Stub().summarize_media("https://x"))
    assert out is None


def test_default_agentic_search_raises_capability():
    class Stub(LLMRunner):
        name = "stub"

        def health_check(self):
            return True

        def run(self, prompt, *, schema=None):
            return {}

    with pytest.raises(CapabilityUnavailableError):
        asyncio.run(Stub().agentic_search("q"))


def test_agentic_search_dataclasses():
    cite = AgenticSearchCitation(url="https://x", title="t")
    assert cite.url == "https://x"
    res = AgenticSearchResult(answer="a")
    assert res.citations == []


class TestJsonCliRunnerHelpers:
    def _make(self):
        runner = ClaudeRunner()
        return runner

    def test_health_check_no_binary(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda b: None)
        cfg = MagicMock()
        cfg.llm_settings.return_value = {"binary": "missing"}
        with patch("social_research_probe.technologies.llms.load_active_config", return_value=cfg):
            assert self._make().health_check() is False

    def test_parse_response_invalid_json_raises(self):
        runner = self._make()
        with pytest.raises(AdapterError):
            runner._parse_response("not json")

    def test_parse_response_valid(self):
        runner = self._make()
        assert runner._parse_response('{"a":1}') == {"a": 1}

    def test_build_argv_with_schema(self):
        runner = self._make()
        cfg = MagicMock()
        cfg.llm_settings.return_value = {"binary": "claude", "extra_flags": ["-x"]}
        with patch("social_research_probe.technologies.llms.load_active_config", return_value=cfg):
            argv = runner._build_argv({"type": "object"})
        assert "claude" in argv[0]
        assert "--json-schema" in argv

    def test_run_invokes_subprocess(self, monkeypatch):
        runner = ClaudeRunner()
        cfg = MagicMock()
        cfg.llm_settings.return_value = {"binary": "claude"}
        cfg.llm_timeout_seconds = 10
        result = MagicMock(stdout='{"k": 1}')

        def fake_sp_run(argv, **kw):
            return result

        with (
            patch("social_research_probe.technologies.llms.load_active_config", return_value=cfg),
            patch("social_research_probe.utils.io.subprocess_runner.run", side_effect=fake_sp_run),
        ):
            assert runner.run("prompt") == {"k": 1}


class TestClaudeSearchBodyParser:
    def test_json_block(self):
        body = '{"answer": "x", "citations": [{"url": "https://a", "title": "T"}]}'
        answer, citations = _parse_claude_search_body(body)
        assert answer == "x"
        assert citations == [AgenticSearchCitation(url="https://a", title="T")]

    def test_fenced_json(self):
        body = '```json\n{"answer": "y", "citations": []}\n```'
        answer, citations = _parse_claude_search_body(body)
        assert answer == "y"
        assert citations == []

    def test_fallback_to_urls(self):
        body = "see https://x.com and https://y.com for more"
        _answer, citations = _parse_claude_search_body(body)
        assert "https://x.com" in body
        urls = [c.url for c in citations]
        assert "https://x.com" in urls and "https://y.com" in urls

    def test_drops_dict_without_url(self):
        body = '{"answer": "x", "citations": [{"title": "no url"}]}'
        _, citations = _parse_claude_search_body(body)
        assert citations == []


class TestRunnerNames:
    def test_claude(self):
        assert ClaudeRunner.name == "claude"
        assert ClaudeRunner.supports_agentic_search is True

    def test_codex(self):
        assert CodexRunner.name == "codex"

    def test_gemini(self):
        assert GeminiRunner.name == "gemini"
