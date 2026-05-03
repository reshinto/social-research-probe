"""Tests for YouTubeNarrativesStage pipeline integration."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from social_research_probe.platforms.state import PipelineState
from social_research_probe.platforms.youtube import YouTubeNarrativesStage, YouTubePipeline


def _mock_cfg() -> MagicMock:
    cfg = MagicMock()
    cfg.raw = {
        "platforms": {"youtube": {"narratives": {"min_cluster_size": 2, "max_cluster_size": 12}}}
    }
    cfg.technology_enabled.return_value = True
    cfg.debug_enabled.return_value = False
    cfg.service_enabled.return_value = True
    cfg.stage_enabled.return_value = True
    return cfg


def _state_with_corroborate(items: list[dict], enabled: bool = True) -> PipelineState:
    state = PipelineState(platform_type="youtube", cmd=MagicMock(), cache=None)
    state.set_stage_output("corroborate", {"top_n": items})
    state.platform_config = {"stages": {"youtube": {"narratives": enabled}}}
    return state


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


class TestNarrativesStageBasic:
    def test_stage_name(self) -> None:
        assert YouTubeNarrativesStage().stage_name == "narratives"

    def test_disabled_passthrough(self) -> None:
        items = [_item("v1", [_claim("c1", ["AI"]), _claim("c2", ["AI"])])]
        state = _state_with_corroborate(items, enabled=False)

        with patch(
            "social_research_probe.config.load_active_config",
            return_value=_mock_cfg(),
        ):
            cfg = _mock_cfg()
            cfg.stage_enabled.return_value = False
            with patch(
                "social_research_probe.config.load_active_config",
                return_value=cfg,
            ):
                result = asyncio.run(YouTubeNarrativesStage().execute(state))

        output = result.get_stage_output("narratives")
        assert output["top_n"] == items
        assert output["clusters"] == []

    def test_empty_top_n_passthrough(self) -> None:
        state = _state_with_corroborate([])
        with patch(
            "social_research_probe.config.load_active_config",
            return_value=_mock_cfg(),
        ):
            result = asyncio.run(YouTubeNarrativesStage().execute(state))
        output = result.get_stage_output("narratives")
        assert output["top_n"] == []
        assert output["clusters"] == []


class TestNarrativesStageEnabled:
    def test_produces_clusters(self) -> None:
        items = [
            _item("v1", [_claim("c1", ["AI"]), _claim("c2", ["AI"])]),
            _item("v2", [_claim("c3", ["AI"])]),
        ]
        state = _state_with_corroborate(items)
        mock_cfg = _mock_cfg()

        with (
            patch("social_research_probe.config.load_active_config", return_value=mock_cfg),
            patch("social_research_probe.technologies.load_active_config", return_value=mock_cfg),
            patch(
                "social_research_probe.technologies.narratives.load_active_config",
                return_value=mock_cfg,
            ),
        ):
            result = asyncio.run(YouTubeNarrativesStage().execute(state))

        output = result.get_stage_output("narratives")
        assert len(output["clusters"]) >= 1
        assert output["clusters"][0]["claim_count"] >= 2

    def test_items_annotated_with_narrative_ids(self) -> None:
        items = [
            _item("v1", [_claim("c1", ["AI"]), _claim("c2", ["AI"])]),
        ]
        state = _state_with_corroborate(items)
        mock_cfg = _mock_cfg()

        with (
            patch("social_research_probe.config.load_active_config", return_value=mock_cfg),
            patch("social_research_probe.technologies.load_active_config", return_value=mock_cfg),
            patch(
                "social_research_probe.technologies.narratives.load_active_config",
                return_value=mock_cfg,
            ),
        ):
            result = asyncio.run(YouTubeNarrativesStage().execute(state))

        output = result.get_stage_output("narratives")
        for item in output["top_n"]:
            assert "narrative_ids" in item
            assert len(item["narrative_ids"]) >= 1

    def test_non_dict_item_in_top_n_skipped(self) -> None:
        items: list = [
            _item("v1", [_claim("c1", ["AI"]), _claim("c2", ["AI"])]),
            "not_a_dict",
        ]
        state = _state_with_corroborate(items)
        mock_cfg = _mock_cfg()

        with (
            patch("social_research_probe.config.load_active_config", return_value=mock_cfg),
            patch("social_research_probe.technologies.load_active_config", return_value=mock_cfg),
            patch(
                "social_research_probe.technologies.narratives.load_active_config",
                return_value=mock_cfg,
            ),
        ):
            result = asyncio.run(YouTubeNarrativesStage().execute(state))

        output = result.get_stage_output("narratives")
        assert "not_a_dict" in output["top_n"]

    def test_failed_tech_result_yields_empty_clusters(self) -> None:
        items = [_item("v1", [_claim("c1", ["AI"]), _claim("c2", ["AI"])])]
        state = _state_with_corroborate(items)
        mock_cfg = _mock_cfg()

        failed_tr = MagicMock()
        failed_tr.success = False
        mock_result = MagicMock()
        mock_result.tech_results = [failed_tr]
        mock_service = MagicMock()
        mock_service.execute_batch = AsyncMock(return_value=[mock_result])

        with (
            patch("social_research_probe.config.load_active_config", return_value=mock_cfg),
            patch("social_research_probe.technologies.load_active_config", return_value=mock_cfg),
            patch(
                "social_research_probe.technologies.narratives.load_active_config",
                return_value=mock_cfg,
            ),
            patch(
                "social_research_probe.services.analyzing.narratives.NarrativeClusteringService",
                return_value=mock_service,
            ),
        ):
            result = asyncio.run(YouTubeNarrativesStage().execute(state))

        output = result.get_stage_output("narratives")
        assert output["clusters"] == []

    def test_non_dict_claim_in_extracted_claims_skipped(self) -> None:
        items = [_item("v1", [_claim("c1", ["AI"]), _claim("c2", ["AI"]), "bad_claim"])]
        state = _state_with_corroborate(items)
        mock_cfg = _mock_cfg()

        with (
            patch("social_research_probe.config.load_active_config", return_value=mock_cfg),
            patch("social_research_probe.technologies.load_active_config", return_value=mock_cfg),
            patch(
                "social_research_probe.technologies.narratives.load_active_config",
                return_value=mock_cfg,
            ),
        ):
            result = asyncio.run(YouTubeNarrativesStage().execute(state))

        output = result.get_stage_output("narratives")
        assert "narrative_ids" in output["top_n"][0]


class TestPipelineStageOrder:
    def test_narratives_stage_in_pipeline(self) -> None:
        pipeline = YouTubePipeline()
        stage_names = [s.stage_name for group in pipeline.stages() for s in group]
        assert "narratives" in stage_names

    def test_narratives_after_corroborate_before_synthesis(self) -> None:
        pipeline = YouTubePipeline()
        stage_names = [s.stage_name for group in pipeline.stages() for s in group]
        corr_idx = stage_names.index("corroborate")
        narr_idx = stage_names.index("narratives")
        synth_idx = stage_names.index("synthesis")
        assert corr_idx < narr_idx < synth_idx


class TestSynthesisReadsFromNarratives:
    def test_synthesis_context_uses_narratives_top_n(self) -> None:
        from social_research_probe.platforms.youtube.synthesis_stage import YouTubeSynthesisStage

        state = PipelineState(platform_type="youtube", cmd=MagicMock(), cache=None)
        state.inputs["topic"] = "test"
        state.set_stage_output("narratives", {"top_n": [{"id": "from_narratives"}], "clusters": []})
        state.set_stage_output("corroborate", {"top_n": [{"id": "from_corroborate"}]})
        state.set_stage_output("score", {"top_n": []})
        state.set_stage_output("fetch", {"items": [], "engagement_metrics": []})
        state.set_stage_output("stats", {})
        state.set_stage_output("charts", {})

        stage = YouTubeSynthesisStage()
        ctx = stage._build_synthesis_context(state)
        assert ctx["top_n"][0]["id"] == "from_narratives"


class TestAssembleAttachesNarratives:
    def test_report_has_narratives_key(self) -> None:
        from social_research_probe.platforms.youtube.assemble_stage import YouTubeAssembleStage

        state = PipelineState(platform_type="youtube", cmd=MagicMock(), cache=None)
        state.inputs["topic"] = "test"
        state.inputs["purpose_names"] = []
        state.set_stage_output("narratives", {"top_n": [], "clusters": [{"narrative_id": "n1"}]})
        state.set_stage_output("corroborate", {"top_n": []})
        state.set_stage_output("score", {"top_n": []})
        state.set_stage_output("fetch", {"items": [], "engagement_metrics": []})
        state.set_stage_output("stats", {"stats_summary": {}})
        state.set_stage_output("charts", {"chart_captions": [], "chart_takeaways": []})

        mock_cfg = MagicMock()
        mock_cfg.stage_enabled.return_value = True
        mock_cfg.debug_enabled.return_value = False
        mock_cfg.tunables = {"summary_divergence_threshold": 0.4}

        with patch("social_research_probe.config.load_active_config", return_value=mock_cfg):
            result = asyncio.run(YouTubeAssembleStage().execute(state))

        report = result.outputs["report"]
        assert report["narratives"] == [{"narrative_id": "n1"}]
