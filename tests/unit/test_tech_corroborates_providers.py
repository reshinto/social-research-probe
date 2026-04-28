"""Tests for corroborate providers (exa, brave, tavily, llm_search)."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from unittest.mock import patch

import pytest

from social_research_probe.technologies.corroborates import (
    CorroborationProvider,
    CorroborationResult,
)
from social_research_probe.technologies.corroborates.brave import BraveProvider
from social_research_probe.technologies.corroborates.exa import ExaProvider
from social_research_probe.technologies.corroborates.llm_search import (
    LLMSearchProvider,
    _build_prompt,
    _coerce_confidence,
    _coerce_sources,
    _coerce_verdict,
    _format_origin_sources,
    _parse_response,
)
from social_research_probe.technologies.corroborates.tavily import TavilyProvider
from social_research_probe.utils.core.errors import AdapterError


@dataclass
class _Claim:
    text: str
    source_url: str | None = None


def test_corroboration_result_defaults():
    r = CorroborationResult(verdict="supported", confidence=0.5, reasoning="x")
    assert r.sources == []
    assert r.provider_name == ""


def test_corroboration_provider_is_abc():
    with pytest.raises(TypeError):
        CorroborationProvider()  # type: ignore[abstract]


class TestExa:
    def test_health_check_no_key(self, monkeypatch):
        monkeypatch.delenv("SRP_EXA_API_KEY", raising=False)
        with patch(
            "social_research_probe.technologies.corroborates.exa.read_runtime_secret",
            return_value=None,
        ):
            assert ExaProvider().health_check() is False

    def test_health_check_with_key(self):
        with patch(
            "social_research_probe.technologies.corroborates.exa.read_runtime_secret",
            return_value="key",
        ):
            assert ExaProvider().health_check() is True

    def test_api_key_missing_raises(self):
        with (
            patch(
                "social_research_probe.technologies.corroborates.exa.read_runtime_secret",
                return_value=None,
            ),
            pytest.raises(AdapterError),
        ):
            ExaProvider()._api_key()

    def test_build_result_no_sources(self):
        r = ExaProvider()._build_result(_Claim("c"), [])
        assert r.verdict == "inconclusive"
        assert r.confidence == 0.0

    def test_build_result_with_sources(self):
        raw = [{"url": "https://a.com"}, {"url": "https://b.com"}]
        r = ExaProvider()._build_result(_Claim("c"), raw)
        assert r.verdict == "supported"
        assert r.confidence == 0.4
        assert r.sources == ["https://a.com", "https://b.com"]

    def test_build_result_filters_self_source(self):
        raw = [{"url": "https://x.com/y"}, {"url": "https://other.com"}]
        r = ExaProvider()._build_result(_Claim("c", source_url="https://x.com/y"), raw)
        assert r.sources == ["https://other.com"]


class TestBrave:
    def test_health_check_with_key(self):
        with patch(
            "social_research_probe.technologies.corroborates.brave.read_runtime_secret",
            return_value="k",
        ):
            assert BraveProvider().health_check() is True


class TestTavily:
    def test_health_check_with_key(self):
        with patch(
            "social_research_probe.technologies.corroborates.tavily.read_runtime_secret",
            return_value="k",
        ):
            assert TavilyProvider().health_check() is True


class TestLLMSearchHelpers:
    def test_format_origin_sources_empty(self):
        assert "(none provided)" in _format_origin_sources([])

    def test_format_origin_sources_basic(self):
        out = _format_origin_sources(["https://a", "", "https://b"])
        assert "https://a" in out and "https://b" in out

    def test_build_prompt_calls_template(self):
        prompt = _build_prompt("the claim", ["https://a"])
        assert "the claim" in prompt

    def test_coerce_verdict_valid(self):
        assert _coerce_verdict("supported") == "supported"

    def test_coerce_verdict_invalid(self):
        assert _coerce_verdict("???") == "inconclusive"
        assert _coerce_verdict(None) == "inconclusive"

    def test_coerce_confidence_clamps(self):
        assert _coerce_confidence(2.0) == 1.0
        assert _coerce_confidence(-1.0) == 0.0
        assert _coerce_confidence("nope") == 0.0
        assert _coerce_confidence(0.5) == 0.5

    def test_coerce_sources(self):
        assert _coerce_sources(["a", "", "b"]) == ["a", "b"]
        assert _coerce_sources("not a list") == []

    def test_parse_response_full(self):
        v, c, r, s = _parse_response(
            {
                "verdict": "supported",
                "confidence": 0.7,
                "reasoning": "yes",
                "sources": ["https://a"],
            }
        )
        assert v == "supported" and c == 0.7 and r == "yes" and s == ["https://a"]

    def test_parse_response_defaults(self):
        v, c, r, s = _parse_response({})
        assert v == "inconclusive" and c == 0.0 and r == "" and s == []


class TestLLMSearchProvider:
    def test_origin_urls(self):
        assert LLMSearchProvider._origin_urls_for(_Claim("c", "https://x")) == ["https://x"]
        assert LLMSearchProvider._origin_urls_for(_Claim("c")) == []

    def test_build_result_defaults_reasoning(self):
        out = LLMSearchProvider()._build_result({"verdict": "supported", "confidence": 0.5})
        assert out.reasoning == "LLM returned no reasoning."
        assert out.provider_name == "llm_search"

    def test_corroborate_calls_llm(self, monkeypatch):
        provider = LLMSearchProvider()

        async def fake_ask(self, text, urls):
            return {"verdict": "refuted", "confidence": 0.3, "reasoning": "no", "sources": []}

        monkeypatch.setattr(LLMSearchProvider, "_ask_llm", fake_ask)
        result = asyncio.run(provider.corroborate(_Claim("the claim text")))
        assert result.verdict == "refuted"
        assert result.confidence == 0.3
