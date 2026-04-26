"""Tests for service classes (scoring/synthesis/charts/statistics/summary/transcript/corroboration/html/audio)."""

from __future__ import annotations

import asyncio

from social_research_probe.services.scoring.score import ScoringService


class TestScoringService:
    def test_no_techs(self):
        assert ScoringService()._get_technologies() == []

    def test_execute_one_basic(self):
        svc = ScoringService()
        items = [
            {"id": "1", "trust": 0.8, "trend": 0.5, "opportunity": 0.4},
            {"id": "2", "trust": 0.3, "trend": 0.2, "opportunity": 0.1},
        ]
        out = asyncio.run(svc.execute_one({"items": items}))
        scored = out.tech_results[0].output
        assert len(scored) == 2
        assert all("overall_score" in d for d in scored)

    def test_execute_one_with_weights(self):
        svc = ScoringService()
        items = [{"id": "1", "trust": 1.0, "trend": 0.0, "opportunity": 0.0}]
        out = asyncio.run(svc.execute_one({"items": items, "weights": {"trust": 1.0}}))
        scored = out.tech_results[0].output
        assert scored[0]["overall_score"] == 1.0

    def test_execute_one_non_dict(self):
        svc = ScoringService()
        out = asyncio.run(svc.execute_one("not a dict"))
        assert out.tech_results[0].output == []
