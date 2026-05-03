"""Unit tests for NarrativeClusteringService."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

from social_research_probe.services.analyzing.narratives import NarrativeClusteringService
from social_research_probe.technologies.narratives import NarrativeClustererTech


class TestNarrativeClusteringServiceMeta:
    def test_service_name(self) -> None:
        assert NarrativeClusteringService.service_name == "youtube.analyzing.narratives"

    def test_enabled_config_key(self) -> None:
        assert (
            NarrativeClusteringService.enabled_config_key == "services.youtube.analyzing.narratives"
        )

    def test_get_technologies_returns_clusterer(self) -> None:
        svc = NarrativeClusteringService()
        techs = svc._get_technologies()
        assert len(techs) == 1
        assert isinstance(techs[0], NarrativeClustererTech)


def _make_config_mock() -> MagicMock:
    cfg = MagicMock()
    cfg.raw = {
        "platforms": {"youtube": {"narratives": {"min_cluster_size": 2, "max_cluster_size": 12}}}
    }
    cfg.technology_enabled.return_value = True
    cfg.debug_enabled.return_value = False
    cfg.service_enabled.return_value = True
    return cfg


class TestNarrativeClusteringServiceExecute:
    def test_execute_batch_returns_clusters(self) -> None:
        items = [
            {
                "id": "v1",
                "url": "https://example.com/v1",
                "extracted_claims": [
                    {
                        "claim_id": "c1",
                        "claim_text": "AI will grow",
                        "claim_type": "prediction",
                        "entities": ["AI"],
                        "confidence": 0.8,
                        "evidence_tier": "transcript_rich",
                        "corroboration_status": "pending",
                        "contradiction_status": "none",
                        "needs_review": False,
                        "position_in_text": 1,
                        "extracted_at": "2024-01-01",
                    },
                    {
                        "claim_id": "c2",
                        "claim_text": "AI needs regulation",
                        "claim_type": "opinion",
                        "entities": ["AI"],
                        "confidence": 0.6,
                        "evidence_tier": "transcript_rich",
                        "corroboration_status": "pending",
                        "contradiction_status": "none",
                        "needs_review": False,
                        "position_in_text": 5,
                        "extracted_at": "2024-01-01",
                    },
                ],
            }
        ]

        mock_cfg = _make_config_mock()

        with (
            patch(
                "social_research_probe.config.load_active_config",
                return_value=mock_cfg,
            ),
            patch(
                "social_research_probe.technologies.load_active_config",
                return_value=mock_cfg,
            ),
            patch(
                "social_research_probe.technologies.narratives.load_active_config",
                return_value=mock_cfg,
            ),
        ):
            result = asyncio.run(NarrativeClusteringService().execute_batch([{"items": items}]))

        assert len(result) == 1
        tech_results = result[0].tech_results
        assert len(tech_results) >= 1
        output = tech_results[0].output
        assert isinstance(output, dict)
        assert "clusters" in output
