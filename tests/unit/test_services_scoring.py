"""Tests for services.scoring (compute, weights)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from social_research_probe.services import ServiceResult, TechResult
from social_research_probe.services.scoring import resolve_scoring_weights
from social_research_probe.services.scoring.score import ScoringService
from social_research_probe.technologies.scoring.combine import DEFAULT_WEIGHTS
from social_research_probe.utils.purposes.merge import MergedPurpose


@pytest.fixture()
def service():
    return ScoringService()


@pytest.mark.asyncio
async def test_execute_service_extracts_scored_list(service):
    scored_items = [{"id": "x", "score": 0.9}, {"id": "y", "score": 0.5}]
    data = {"items": [{"id": "x"}], "engagement_metrics": [], "weights": {}, "limit": 1}
    service_result = ServiceResult(
        service_name=service.service_name,
        input_key="score",
        tech_results=[
            TechResult(tech_name="scoring", input=data, success=True, output=scored_items)
        ],
    )

    result = await service.execute_service(data, service_result)

    assert result.tech_results[0].output == {
        "all_scored": scored_items,
        "top_n": scored_items[:1],
    }


@pytest.mark.asyncio
async def test_execute_service_no_successful_tech_result_returns_empty(service):
    data = {"items": [{"id": "x"}], "engagement_metrics": [], "weights": {}, "limit": 5}
    service_result = ServiceResult(
        service_name=service.service_name,
        input_key="score",
        tech_results=[TechResult(tech_name="scoring", input=data, success=False, output=None)],
    )

    result = await service.execute_service(data, service_result)

    assert result.tech_results[0].output == {"all_scored": [], "top_n": []}


@pytest.mark.asyncio
async def test_execute_service_with_empty_result_keeps_empty_result(service):
    service_result = ServiceResult(
        service_name=service.service_name,
        input_key="score",
        tech_results=[],
    )

    result = await service.execute_service({"items": [], "limit": 1}, service_result)

    assert result.tech_results == []


def _merged(**overrides) -> MergedPurpose:
    return MergedPurpose(
        names=("default",),
        method="",
        evidence_priorities=(),
        scoring_overrides=overrides,
    )


class TestResolveWeights:
    def test_returns_default_weights_when_no_config_overrides(self, monkeypatch):
        fake_cfg = MagicMock()
        fake_cfg.raw = {}
        monkeypatch.setattr(
            "social_research_probe.config.load_active_config",
            lambda: fake_cfg,
        )
        result = resolve_scoring_weights(_merged())
        assert result == dict(DEFAULT_WEIGHTS)

    def test_config_weights_override_defaults(self, monkeypatch):
        fake_cfg = MagicMock()
        fake_cfg.raw = {"scoring": {"weights": {"trust": 0.9}}}
        monkeypatch.setattr(
            "social_research_probe.config.load_active_config",
            lambda: fake_cfg,
        )
        result = resolve_scoring_weights(_merged())
        assert result["trust"] == 0.9

    def test_purpose_overrides_win_over_config(self, monkeypatch):
        fake_cfg = MagicMock()
        fake_cfg.raw = {"scoring": {"weights": {"trend": 0.5}}}
        monkeypatch.setattr(
            "social_research_probe.config.load_active_config",
            lambda: fake_cfg,
        )
        result = resolve_scoring_weights(_merged(trend=0.1))
        assert result["trend"] == 0.1

    def test_unknown_keys_ignored(self, monkeypatch):
        fake_cfg = MagicMock()
        fake_cfg.raw = {"scoring": {"weights": {"bogus": 99.0}}}
        monkeypatch.setattr(
            "social_research_probe.config.load_active_config",
            lambda: fake_cfg,
        )
        result = resolve_scoring_weights(_merged())
        assert "bogus" not in result
