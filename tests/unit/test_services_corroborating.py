"""Tests for services.corroborating (host, providers, registry)."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest

from social_research_probe.services import corroborating as providers
from social_research_probe.services import corroborating as registry
from social_research_probe.technologies import corroborates as host
from social_research_probe.technologies.corroborates import (
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

    def test_register_get(self, monkeypatch):
        class P(CorroborationProvider):
            name = "test_register_get_p"

            def health_check(self):
                return True

            async def corroborate(self, claim):
                return _result("supported", 0.5)

        cfg = MagicMock()
        cfg.technology_enabled.return_value = True
        monkeypatch.setattr("social_research_probe.config.load_active_config", lambda *a, **k: cfg)
        registry.register(P)
        assert isinstance(registry.get_provider("test_register_get_p"), P)
        assert "test_register_get_p" in registry.list_providers()

    def test_ensure_registered_runs(self):
        registry.ensure_providers_registered()


class TestProviders:
    def test_auto_mode_returns_all_when_service_enabled(self, monkeypatch):
        cfg = MagicMock()
        cfg.service_enabled.return_value = True
        monkeypatch.setattr("social_research_probe.config.load_active_config", lambda *a, **k: cfg)
        out = providers.auto_mode_providers()
        assert out == ("exa", "brave", "tavily", "llm_search")

    def test_auto_mode_returns_empty_when_service_disabled(self, monkeypatch):
        cfg = MagicMock()
        cfg.service_enabled.return_value = False
        monkeypatch.setattr("social_research_probe.config.load_active_config", lambda *a, **k: cfg)
        out = providers.auto_mode_providers()
        assert out == ()


class TestCorroborateClaim:
    def test_returns_result(self, monkeypatch):
        class P(CorroborationProvider):
            name = "fake1"

            def health_check(self):
                return True

            async def corroborate(self, claim):
                return _result("supported", 0.7)

        monkeypatch.setattr(host, "get_provider", lambda n: P())
        claim = MagicMock()
        claim.text = "the claim"
        out = asyncio.run(host.corroborate_claim(claim, ["fake1"]))
        assert out["aggregate_verdict"] == "supported"
        assert out["claim_text"] == "the claim"

    def test_provider_error_skipped(self, monkeypatch):
        class P(CorroborationProvider):
            name = "fakefail"

            def health_check(self):
                return True

            async def corroborate(self, claim):
                raise RuntimeError("boom")

        monkeypatch.setattr(host, "get_provider", lambda n: P())
        claim = MagicMock()
        claim.text = "x"
        out = asyncio.run(host.corroborate_claim(claim, ["fakefail"]))
        assert out["results"] == []
