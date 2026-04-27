"""Tests for service classes (scoring/synthesis/charts/statistics/summary/transcript/corroboration/html/audio)."""

from __future__ import annotations

import asyncio

from social_research_probe.services.scoring.score import ScoringService


class TestScoringService:
    def test_techs(self):
        techs = ScoringService()._get_technologies()
        assert techs[0].name == "scoring.compute"

    def test_execute_one_basic(self, monkeypatch):
        monkeypatch.setattr(
            "social_research_probe.services.scoring.score_items",
            lambda i, m, w: [{"overall_score": 1.0}, {"overall_score": 0.5}],
        )
        svc = ScoringService()
        items = [{"id": "1"}, {"id": "2"}]
        out = asyncio.run(svc.execute_one({"items": items}))
        scored = out.tech_results[0].output
        assert len(scored) == 2
        assert all("overall_score" in d for d in scored)

    def test_execute_one_with_weights(self, monkeypatch):
        monkeypatch.setattr(
            "social_research_probe.services.scoring.score_items",
            lambda i, m, w: [{"overall_score": w.get("trust", 0.0)}],
        )
        svc = ScoringService()
        items = [{"id": "1"}]
        out = asyncio.run(svc.execute_one({"items": items, "weights": {"trust": 1.0}}))
        scored = out.tech_results[0].output
        assert scored[0]["overall_score"] == 1.0

    def test_execute_one_non_dict(self):
        svc = ScoringService()
        out = asyncio.run(svc.execute_one("not a dict"))
        assert out.tech_results[0].output == []
