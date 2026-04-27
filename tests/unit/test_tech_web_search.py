"""Tests for technologies.web_search wrapper classes."""

from __future__ import annotations

import asyncio

from social_research_probe.technologies.llms import AgenticSearchResult
from social_research_probe.technologies.web_search.claude_search import ClaudeWebSearch
from social_research_probe.technologies.web_search.codex_search import CodexWebSearch
from social_research_probe.technologies.web_search.gemini_search import GeminiWebSearch


def _stub_search(self, query, *, max_results=5, timeout_s=60.0):
    async def _coro():
        return AgenticSearchResult(answer=query, citations=[], runner_name=self.name)

    return _coro()


def test_claude_web_search_execute(monkeypatch):
    monkeypatch.setattr(ClaudeWebSearch, "agentic_search", _stub_search)
    out = asyncio.run(ClaudeWebSearch()._execute("hello"))
    assert out.answer == "hello"


def test_codex_web_search_execute(monkeypatch):
    monkeypatch.setattr(CodexWebSearch, "agentic_search", _stub_search)
    out = asyncio.run(CodexWebSearch()._execute("foo"))
    assert out.answer == "foo"


def test_gemini_web_search_execute(monkeypatch):
    monkeypatch.setattr(GeminiWebSearch, "agentic_search", _stub_search)
    out = asyncio.run(GeminiWebSearch()._execute("bar"))
    assert out.answer == "bar"


def test_class_names():
    assert ClaudeWebSearch.name == "claude_web_search"
    assert CodexWebSearch.name == "codex_web_search"
    assert GeminiWebSearch.name == "gemini_web_search"
