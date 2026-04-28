"""Tests for services.classifying.source_class."""

from __future__ import annotations

import pytest

from social_research_probe.services.classifying.source_class import (
    SourceClassService,
    resolve_provider_name,
)
from social_research_probe.technologies.classifying import (
    HeuristicClassifier,
    HybridClassifier,
    LLMClassifier,
)


class FakeConfig:
    def __init__(self, *, provider: str = "hybrid", enabled: bool = True) -> None:
        self.raw = {"services": {"youtube": {"classifying": {"provider": provider}}}}
        self._enabled = enabled

    def service_enabled(self, name: str) -> bool:
        return self._enabled

    def technology_enabled(self, name: str) -> bool:
        return self._enabled


def _patch_cfg(monkeypatch, cfg: FakeConfig) -> None:
    from social_research_probe import config as cfg_mod

    monkeypatch.setattr(cfg_mod, "load_active_config", lambda: cfg)


class TestResolveProviderName:
    def test_default(self, monkeypatch):
        _patch_cfg(monkeypatch, FakeConfig(provider="hybrid"))
        assert resolve_provider_name() == "hybrid"

    def test_heuristic(self, monkeypatch):
        _patch_cfg(monkeypatch, FakeConfig(provider="heuristic"))
        assert resolve_provider_name() == "heuristic"

    def test_llm(self, monkeypatch):
        _patch_cfg(monkeypatch, FakeConfig(provider="llm"))
        assert resolve_provider_name() == "llm"

    def test_unknown_falls_back_to_hybrid(self, monkeypatch):
        _patch_cfg(monkeypatch, FakeConfig(provider="bogus"))
        assert resolve_provider_name() == "hybrid"

    def test_case_insensitive(self, monkeypatch):
        _patch_cfg(monkeypatch, FakeConfig(provider="HEURISTIC"))
        assert resolve_provider_name() == "heuristic"


class TestGetTechnologies:
    def test_heuristic_provider(self, monkeypatch):
        _patch_cfg(monkeypatch, FakeConfig(provider="heuristic"))
        techs = SourceClassService()._get_technologies()
        assert len(techs) == 1
        assert isinstance(techs[0], HeuristicClassifier)

    def test_llm_provider(self, monkeypatch):
        _patch_cfg(monkeypatch, FakeConfig(provider="llm"))
        techs = SourceClassService()._get_technologies()
        assert isinstance(techs[0], LLMClassifier)

    def test_hybrid_provider(self, monkeypatch):
        _patch_cfg(monkeypatch, FakeConfig(provider="hybrid"))
        techs = SourceClassService()._get_technologies()
        assert isinstance(techs[0], HybridClassifier)


class TestServiceExecuteOne:
    @pytest.mark.asyncio
    async def test_returns_classification(self, monkeypatch):
        _patch_cfg(monkeypatch, FakeConfig(provider="heuristic"))
        result = await SourceClassService().execute_one({"channel": "BBC News", "title": "x"})
        assert any(tr.success and tr.output == "primary" for tr in result.tech_results)

    @pytest.mark.asyncio
    async def test_unknown_when_no_signal(self, monkeypatch):
        _patch_cfg(monkeypatch, FakeConfig(provider="heuristic"))
        result = await SourceClassService().execute_one(
            {"channel": "Random Indie", "title": "behind the scenes"}
        )
        assert result.tech_results[0].output == "unknown"
