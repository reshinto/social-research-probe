"""Tests for services.scoring (compute, weights)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from social_research_probe.services import TechResult
from social_research_probe.services.scoring.score import ScoringService


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
