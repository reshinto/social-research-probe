"""Unit tests for CorroborationService.__init__ and corroborate_batch."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

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


class TestCorroborateBatch:
    def test_no_providers_returns_list_unchanged(self):
        svc = CorroborationService(providers=[])
        items = [{"title": "a"}, {"title": "b"}]
        result = asyncio.run(svc.corroborate_batch(items))
        assert result == items

    def test_merges_corroboration_into_items(self, monkeypatch):
        svc = CorroborationService(providers=["exa"])
        corr_data = {"aggregate_verdict": "supported", "confidence": 0.9}
        fake_results = [
            _service_result(corr_data),
            _service_result(None),
        ]
        monkeypatch.setattr(
            svc,
            "execute_batch",
            AsyncMock(return_value=fake_results),
        )
        items = [{"title": "first"}, {"title": "second"}]
        result = asyncio.run(svc.corroborate_batch(items))
        assert result[0]["corroboration"] == corr_data
        assert result[0]["title"] == "first"
        assert "corroboration" not in result[1]
        assert result[1]["title"] == "second"

    def test_non_dict_items_excluded(self, monkeypatch):
        svc = CorroborationService(providers=["exa"])
        corr_data = {"verdict": "supported"}
        fake_results = [
            _service_result(corr_data),
            _service_result(None),
        ]
        monkeypatch.setattr(
            svc,
            "execute_batch",
            AsyncMock(return_value=fake_results),
        )
        items = [{"title": "a"}, "not-a-dict"]
        result = asyncio.run(svc.corroborate_batch(items))
        assert len(result) == 1
        assert result[0]["corroboration"] == corr_data

    def test_all_outputs_none_returns_copies(self, monkeypatch):
        svc = CorroborationService(providers=["exa"])
        fake_results = [_service_result(None), _service_result(None)]
        monkeypatch.setattr(
            svc,
            "execute_batch",
            AsyncMock(return_value=fake_results),
        )
        items = [{"title": "x"}, {"title": "y"}]
        result = asyncio.run(svc.corroborate_batch(items))
        assert result == items
        assert all("corroboration" not in r for r in result)
