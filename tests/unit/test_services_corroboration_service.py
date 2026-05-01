"""Unit tests for CorroborationService.__init__ and execute_service."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

from social_research_probe.services import ServiceResult, TechResult
from social_research_probe.services.corroborating.corroborate import (
    CorroborationService,
)


def _service_result(output):
    tr = TechResult(tech_name="test", input=None, output=output, success=output is not None)
    return ServiceResult(service_name="test", input_key="", tech_results=[tr])


class TestCorroborationServiceInit:
    def test_explicit_providers_used_directly(self):
        svc = CorroborationService(providers=["exa", "brave"])
        assert svc.providers == ["exa", "brave"]

    def test_explicit_empty_providers(self):
        svc = CorroborationService(providers=[])
        assert svc.providers == []

    def test_auto_init_uses_select_healthy_providers(self, monkeypatch):
        cfg = MagicMock()
        cfg.corroboration_provider = "exa"
        monkeypatch.setattr("social_research_probe.config.load_active_config", lambda: cfg)
        monkeypatch.setattr(
            "social_research_probe.services.corroborating.select_healthy_providers",
            lambda configured: (["exa"], ("exa",)),
        )
        monkeypatch.setattr(
            "social_research_probe.utils.display.fast_mode.fast_mode_enabled",
            lambda: False,
        )
        svc = CorroborationService()
        assert svc.providers == ["exa"]

    def test_auto_init_fast_mode_caps_providers(self, monkeypatch):
        cfg = MagicMock()
        cfg.corroboration_provider = "auto"
        monkeypatch.setattr("social_research_probe.config.load_active_config", lambda: cfg)
        monkeypatch.setattr(
            "social_research_probe.services.corroborating.select_healthy_providers",
            lambda configured: (["exa", "brave", "tavily"], ("exa", "brave", "tavily")),
        )
        monkeypatch.setattr(
            "social_research_probe.utils.display.fast_mode.fast_mode_enabled",
            lambda: True,
        )
        monkeypatch.setattr(
            "social_research_probe.utils.display.fast_mode.FAST_MODE_MAX_PROVIDERS",
            1,
        )
        svc = CorroborationService()
        assert svc.providers == ["exa"]

    def test_auto_init_logs_when_no_healthy_providers(self, monkeypatch):
        cfg = MagicMock()
        cfg.corroboration_provider = "exa"
        monkeypatch.setattr("social_research_probe.config.load_active_config", lambda: cfg)
        monkeypatch.setattr(
            "social_research_probe.services.corroborating.select_healthy_providers",
            lambda configured: ([], ("exa",)),
        )
        monkeypatch.setattr(
            "social_research_probe.utils.display.fast_mode.fast_mode_enabled",
            lambda: False,
        )
        logged = []
        monkeypatch.setattr(
            "social_research_probe.utils.display.progress.log",
            lambda msg: logged.append(msg),
        )
        svc = CorroborationService()
        assert svc.providers == []
        assert any("no provider usable" in m for m in logged)


class TestCorroborateExecuteService:
    def test_merges_corroboration_into_item(self):
        svc = CorroborationService(providers=["exa"])
        corr_data = {"aggregate_verdict": "supported", "confidence": 0.9}
        result = asyncio.run(svc.execute_service({"title": "first"}, _service_result(corr_data)))
        output = result.tech_results[0].output
        assert output["corroboration"] == corr_data
        assert output["title"] == "first"

    def test_non_dict_items_are_not_merged(self):
        svc = CorroborationService(providers=["exa"])
        corr_data = {"verdict": "supported"}
        result = asyncio.run(svc.execute_service("not-a-dict", _service_result(corr_data)))
        assert result.tech_results[0].output == corr_data

    def test_output_none_returns_copy_without_corroboration(self):
        svc = CorroborationService(providers=["exa"])
        result = asyncio.run(svc.execute_service({"title": "x"}, _service_result(None)))
        assert result.tech_results[0].output == {"title": "x"}
        assert "corroboration" not in result.tech_results[0].output

    def test_dict_input_with_empty_result_is_left_empty(self):
        svc = CorroborationService(providers=["exa"])
        result = asyncio.run(
            svc.execute_service(
                {"title": "x"},
                ServiceResult(service_name=svc.service_name, input_key="x", tech_results=[]),
            )
        )
        assert result.tech_results == []
