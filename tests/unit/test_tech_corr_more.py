"""Tests for brave/tavily/exa providers (build_result + corroborate paths)."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from unittest.mock import patch

import pytest

from social_research_probe.technologies.corroborates.brave import BraveProvider
from social_research_probe.technologies.corroborates.exa import ExaProvider
from social_research_probe.technologies.corroborates.tavily import TavilyProvider
from social_research_probe.utils.core.errors import AdapterError


@dataclass
class _Claim:
    text: str
    source_url: str | None = None


class TestBrave:
    def test_health_no_key(self):
        with patch(
            "social_research_probe.technologies.corroborates.brave.read_runtime_secret",
            return_value=None,
        ):
            assert BraveProvider().health_check() is False

    def test_api_key_missing_raises(self):
        with (
            patch(
                "social_research_probe.technologies.corroborates.brave.read_runtime_secret",
                return_value=None,
            ),
            pytest.raises(AdapterError),
        ):
            BraveProvider()._api_key()

    def test_build_result_no_sources(self):
        out = BraveProvider()._build_result(_Claim("c"), [])
        assert out.verdict == "inconclusive"

    def test_build_result_with_sources(self):
        raw = [{"url": "https://a"}, {"url": "https://b"}]
        out = BraveProvider()._build_result(_Claim("c"), raw)
        assert out.verdict == "supported" and out.sources == ["https://a", "https://b"]

    def test_corroborate(self, monkeypatch):
        async def fake_search(self, q):
            return [{"url": "https://a"}]

        monkeypatch.setattr(BraveProvider, "_search", fake_search)
        out = asyncio.run(BraveProvider().corroborate(_Claim("c")))
        assert out.verdict == "supported"


class TestTavily:
    def test_health_no_key(self):
        with patch(
            "social_research_probe.technologies.corroborates.tavily.read_runtime_secret",
            return_value=None,
        ):
            assert TavilyProvider().health_check() is False

    def test_api_key_missing_raises(self):
        with (
            patch(
                "social_research_probe.technologies.corroborates.tavily.read_runtime_secret",
                return_value=None,
            ),
            pytest.raises(AdapterError),
        ):
            TavilyProvider()._api_key()

    def test_build_result_no_sources(self):
        out = TavilyProvider()._build_result(_Claim("c"), [])
        assert out.verdict == "inconclusive"

    def test_build_result_with_sources(self):
        raw = [{"url": "https://a"}, {"url": "https://b"}]
        out = TavilyProvider()._build_result(_Claim("c"), raw)
        assert out.verdict == "supported"

    def test_corroborate(self, monkeypatch):
        async def fake_search(self, q):
            return [{"url": "https://a"}]

        monkeypatch.setattr(TavilyProvider, "_search", fake_search)
        out = asyncio.run(TavilyProvider().corroborate(_Claim("c")))
        assert out.verdict == "supported"


def test_exa_corroborate(monkeypatch):
    async def fake_search(self, q):
        return [{"url": "https://a"}]

    monkeypatch.setattr(ExaProvider, "_search", fake_search)
    out = asyncio.run(ExaProvider().corroborate(_Claim("c")))
    assert out.verdict == "supported"
