"""Tests for services.scoring (compute, weights)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from social_research_probe.services import TechResult
from social_research_probe.services.scoring import resolve_scoring_weights
from social_research_probe.services.scoring.score import ScoringService
from social_research_probe.technologies.scoring.combine import DEFAULT_WEIGHTS
from social_research_probe.utils.purposes.merge import MergedPurpose


@pytest.fixture()
def service():
    return ScoringService()


@pytest.mark.asyncio
async def test_score_and_rank_disabled_returns_passthrough(service):
    items = [{"id": "a"}, {"id": "b"}]
    with patch.object(ScoringService, "is_enabled", return_value=False):
        result = await service.score_and_rank(items, [], {}, limit=1)
    assert result == {"all_scored": items, "top_n": items[:1]}


@pytest.mark.asyncio
async def test_score_and_rank_empty_items_returns_empty(service):
    with patch.object(ScoringService, "is_enabled", return_value=True):
        result = await service.score_and_rank([], [], {}, limit=5)
    assert result == {"all_scored": [], "top_n": []}


@pytest.mark.asyncio
async def test_score_and_rank_success_extracts_scored_list(service):
    items = [{"id": "x"}]
    scored_items = [{"id": "x", "score": 0.9}, {"id": "y", "score": 0.5}]

    tr = TechResult(tech_name="scoring", input=items, success=True, output=scored_items)
    service_result = MagicMock()
    service_result.tech_results = [tr]

    with (
        patch.object(ScoringService, "is_enabled", return_value=True),
        patch.object(service, "execute_one", new=AsyncMock(return_value=service_result)),
    ):
        result = await service.score_and_rank(items, [], {}, limit=1)

    assert result["all_scored"] == scored_items
    assert result["top_n"] == scored_items[:1]


@pytest.mark.asyncio
async def test_score_and_rank_no_successful_tech_result_returns_empty(service):
    items = [{"id": "x"}]

    tr = TechResult(tech_name="scoring", input=items, success=False, output=None)
    service_result = MagicMock()
    service_result.tech_results = [tr]

    with (
        patch.object(ScoringService, "is_enabled", return_value=True),
        patch.object(service, "execute_one", new=AsyncMock(return_value=service_result)),
    ):
        result = await service.score_and_rank(items, [], {}, limit=5)

    assert result == {"all_scored": [], "top_n": []}


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
