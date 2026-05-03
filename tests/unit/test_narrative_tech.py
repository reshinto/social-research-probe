"""Unit tests for NarrativeClustererTech."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

from social_research_probe.technologies.narratives import NarrativeClustererTech


def _mock_cfg(min_cluster_size: int = 2, max_cluster_size: int = 12) -> MagicMock:
    cfg = MagicMock()
    cfg.raw = {
        "platforms": {
            "youtube": {
                "narratives": {
                    "min_cluster_size": min_cluster_size,
                    "max_cluster_size": max_cluster_size,
                }
            }
        }
    }
    return cfg


def _run(data: dict, **kwargs: object) -> dict:
    with patch(
        "social_research_probe.technologies.narratives.load_active_config",
        return_value=_mock_cfg(**kwargs),
    ):
        return asyncio.run(NarrativeClustererTech()._execute(data))


def _item(item_id: str, claims: list[dict]) -> dict:
    return {"id": item_id, "url": f"https://example.com/{item_id}", "extracted_claims": claims}


def _claim(claim_id: str, entities: list[str]) -> dict:
    return {
        "claim_id": claim_id,
        "claim_text": f"Claim {claim_id}",
        "claim_type": "fact_claim",
        "entities": entities,
        "confidence": 0.7,
        "evidence_tier": "transcript_rich",
        "corroboration_status": "pending",
        "contradiction_status": "none",
        "needs_review": False,
        "position_in_text": 1,
        "extracted_at": "2024-01-01T00:00:00",
    }


class TestNarrativeClustererTechMeta:
    def test_name(self) -> None:
        assert NarrativeClustererTech.name == "narrative_clusterer"

    def test_enabled_config_key(self) -> None:
        assert NarrativeClustererTech.enabled_config_key == "narrative_clusterer"


class TestNarrativeClustererTechExecute:
    def test_empty_items_returns_empty_clusters(self) -> None:
        result = _run({"items": []})
        assert result == {"clusters": []}

    def test_items_with_claims_produces_clusters(self) -> None:
        items = [
            _item("v1", [_claim("c1", ["AI"]), _claim("c2", ["AI"])]),
            _item("v2", [_claim("c3", ["AI"])]),
        ]
        result = _run({"items": items})
        assert len(result["clusters"]) >= 1
        assert result["clusters"][0]["claim_count"] >= 2

    def test_respects_config_min_cluster_size(self) -> None:
        items = [_item("v1", [_claim("c1", ["X"]), _claim("c2", ["X"])])]
        result = _run({"items": items}, min_cluster_size=5)
        assert result["clusters"] == []
