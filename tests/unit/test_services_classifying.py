"""Tests for services.classifying.source_class."""

from __future__ import annotations

import pytest

from social_research_probe.services import ServiceResult, TechResult
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
        assert result.tech_results[0].output["source_class"] == "primary"

    @pytest.mark.asyncio
    async def test_unknown_when_no_signal(self, monkeypatch):
        _patch_cfg(monkeypatch, FakeConfig(provider="heuristic"))
        result = await SourceClassService().execute_one(
            {"channel": "Random Indie", "title": "behind the scenes"}
        )
        assert result.tech_results[0].output["source_class"] == "unknown"


class TestExecuteService:
    @pytest.mark.asyncio
    async def test_existing_source_class_preserved(self, monkeypatch):
        _patch_cfg(monkeypatch, FakeConfig(provider="heuristic"))
        item = {"id": "1", "channel": "SomeChannel", "title": "news", "source_class": "primary"}
        service_result = ServiceResult(
            service_name="source_class",
            input_key="x",
            tech_results=[TechResult("heuristic", item, "secondary", True)],
        )
        result = await SourceClassService().execute_service(item, service_result)
        assert result.tech_results[0].output["source_class"] == "primary"

    @pytest.mark.asyncio
    async def test_title_override_commentary(self, monkeypatch):
        _patch_cfg(monkeypatch, FakeConfig(provider="heuristic"))
        item = {"id": "1", "channel": "BBC News", "title": "REACTING to the latest news"}
        service_result = ServiceResult(
            service_name="source_class",
            input_key="x",
            tech_results=[TechResult("heuristic", item, "primary", True)],
        )
        result = await SourceClassService().execute_service(item, service_result)
        assert result.tech_results[0].output["source_class"] == "commentary"

    @pytest.mark.asyncio
    async def test_unknown_when_no_string_tech_output(self, monkeypatch):
        _patch_cfg(monkeypatch, FakeConfig(provider="heuristic"))
        failed_tr = TechResult(
            tech_name="heuristic",
            input={"id": "1"},
            output=None,
            success=False,
        )
        fake_result = ServiceResult(
            service_name="source_class",
            input_key={"id": "1"},
            tech_results=[failed_tr],
        )
        item = {"id": "1", "channel": "UnknownChan", "title": "some video"}
        result = await SourceClassService().execute_service(item, fake_result)
        assert result.tech_results[0].output["source_class"] == "unknown"

    @pytest.mark.asyncio
    async def test_non_dict_input_returns_result_unchanged(self, monkeypatch):
        _patch_cfg(monkeypatch, FakeConfig(provider="heuristic"))
        service_result = ServiceResult(
            service_name="source_class",
            input_key="x",
            tech_results=[TechResult("heuristic", None, "primary", True)],
        )
        result = await SourceClassService().execute_service("raw", service_result)
        assert result is service_result

    @pytest.mark.asyncio
    async def test_empty_result_keeps_normalized_item_without_mutation(self, monkeypatch):
        _patch_cfg(monkeypatch, FakeConfig(provider="heuristic"))
        service_result = ServiceResult(
            service_name="source_class",
            input_key="x",
            tech_results=[],
        )
        result = await SourceClassService().execute_service(
            {"id": "1", "channel": "Unknown", "title": "plain"},
            service_result,
        )
        assert result.tech_results == []
