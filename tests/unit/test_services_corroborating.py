"""Tests for services.corroborating (host, providers, registry)."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from social_research_probe.services.corroborating import host, providers, registry
from social_research_probe.technologies.corroborates.base import (
    CorroborationProvider,
    CorroborationResult,
)
from social_research_probe.utils.core.errors import ValidationError


def _result(verdict, conf):
    return CorroborationResult(verdict=verdict, confidence=conf, reasoning="")


class TestAggregateVerdict:
    def test_empty(self):
        assert host.aggregate_verdict([]) == ("inconclusive", 0.0)

    def test_majority_supported(self):
        out = host.aggregate_verdict(
            [_result("supported", 0.8), _result("supported", 0.6), _result("refuted", 0.5)]
        )
        assert out[0] == "supported"
        assert 0.0 <= out[1] <= 1.0

    def test_tie_inconclusive(self):
        out = host.aggregate_verdict([_result("supported", 0.5), _result("refuted", 0.5)])
        assert out[0] == "inconclusive"

    def test_zero_total_weight(self):
        out = host.aggregate_verdict([_result("supported", 0.0)])
        assert out[1] == 0.0


class TestRegistry:
    def test_register_requires_name(self):
        class Bad(CorroborationProvider):
            name = ""

            def health_check(self):
                return True

            async def corroborate(self, claim):
                return _result("supported", 0.5)

        with pytest.raises(ValueError):
            registry.register(Bad)

    def test_get_unknown(self):
        with pytest.raises(ValidationError):
            registry.get_provider("def-missing")

    def test_register_get(self):
        class P(CorroborationProvider):
            name = "test_register_get_p"

            def health_check(self):
                return True

            async def corroborate(self, claim):
                return _result("supported", 0.5)

        registry.register(P)
        assert isinstance(registry.get_provider("test_register_get_p"), P)
        assert "test_register_get_p" in registry.list_providers()

    def test_ensure_registered_runs(self):
        registry.ensure_providers_registered()


class TestProviders:
    def test_auto_mode_filters(self):
        cfg = MagicMock()
        cfg.technology_enabled.side_effect = lambda n: n in {"exa", "tavily"}
        out = providers.auto_mode_providers(cfg)
        assert out == ("exa", "tavily")


class TestCorroborateClaim:
    def test_returns_result(self, monkeypatch):
        class P(CorroborationProvider):
            name = "fake1"

            def health_check(self):
                return True

            async def corroborate(self, claim):
                return _result("supported", 0.7)

        monkeypatch.setattr(host, "get_provider", lambda n: P())

        with patch.object(host, "get_json", return_value=None), patch.object(host, "set_json"):
            claim = MagicMock()
            claim.text = "the claim"
            out = asyncio.run(host.corroborate_claim(claim, ["fake1"]))
            assert out["aggregate_verdict"] == "supported"
            assert out["claim_text"] == "the claim"

    def test_cached_returned(self):
        with patch.object(host, "get_json", return_value={"cached": True}):
            claim = MagicMock()
            claim.text = "x"
            out = asyncio.run(host.corroborate_claim(claim, ["a"]))
            assert out == {"cached": True}

    def test_provider_error_skipped(self, monkeypatch):
        class P(CorroborationProvider):
            name = "fakefail"

            def health_check(self):
                return True

            async def corroborate(self, claim):
                raise RuntimeError("boom")

        monkeypatch.setattr(host, "get_provider", lambda n: P())
        with patch.object(host, "get_json", return_value=None), patch.object(host, "set_json"):
            claim = MagicMock()
            claim.text = "x"
            out = asyncio.run(host.corroborate_claim(claim, ["fakefail"]))
            assert out["results"] == []


class TestCorroborateItem:
    def test_attaches_corroboration(self, monkeypatch):
        async def fake(claim, names):
            return {"verdict": "x"}

        monkeypatch.setattr(host, "corroborate_claim", fake)
        item = {"title": "t", "url": "https://x"}
        out = asyncio.run(host.corroborate_item(item, ["x"]))
        assert out["corroboration"] == {"verdict": "x"}

    def test_failure_returns_item_copy(self, monkeypatch):
        async def fake(claim, names):
            raise RuntimeError("nope")

        monkeypatch.setattr(host, "corroborate_claim", fake)
        item = {"title": "t"}
        out = asyncio.run(host.corroborate_item(item, ["x"]))
        assert "corroboration" not in out
        assert out["title"] == "t"
