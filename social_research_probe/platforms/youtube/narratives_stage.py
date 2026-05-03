"""YouTubeNarrativesStage implementation."""

from __future__ import annotations

from social_research_probe.platforms import BaseStage
from social_research_probe.platforms.state import PipelineState


class YouTubeNarrativesStage(BaseStage):
    """Cluster claims into narrative groups after corroboration.

    Examples:
        Input:
            YouTubeNarrativesStage
        Output:
            YouTubeNarrativesStage()
    """

    @property
    def stage_name(self) -> str:
        """Return the `narratives` stage key used by config and PipelineState.

        Returns:
            The configured stage name setting.

        Examples:
            Input:
                stage.stage_name
            Output:
                "narratives"
        """
        return "narratives"

    async def execute(self, state: PipelineState) -> PipelineState:
        """Run narrative clustering on corroborated items.

        Reads items from the corroborate stage output, clusters their claims into
        narrative groups, and annotates each item with its narrative_ids.

        Args:
            state: PipelineState carrying config, inputs, and outputs accumulated by earlier stages.

        Returns:
            The same PipelineState instance after this stage has published its output.

        Examples:
            Input:
                await execute(
                    state=PipelineState(platform_type="youtube", cmd=None, cache=None),
                )
            Output:
                PipelineState(platform_type="youtube", cmd=None, cache=None)
        """
        from social_research_probe.services.analyzing.narratives import (
            NarrativeClusteringService,
        )

        top_n = list(state.get_stage_output("corroborate").get("top_n", []))
        if not self._is_enabled(state) or not top_n:
            state.set_stage_output("narratives", {"top_n": top_n, "clusters": []})
            return state

        service = NarrativeClusteringService()
        results = await service.execute_batch([{"items": top_n}])

        clusters: list[dict] = []
        for result in results:
            for tr in result.tech_results:
                if tr.success and isinstance(tr.output, dict):
                    clusters = tr.output.get("clusters", [])
                    break

        claim_to_narratives: dict[str, list[str]] = {}
        for cluster in clusters:
            for cid in cluster.get("claim_ids", []):
                claim_to_narratives.setdefault(cid, []).append(cluster["narrative_id"])

        for item in top_n:
            if not isinstance(item, dict):
                continue
            item_narrative_ids: set[str] = set()
            for claim in item.get("extracted_claims", []):
                if isinstance(claim, dict):
                    for nid in claim_to_narratives.get(claim.get("claim_id", ""), []):
                        item_narrative_ids.add(nid)
            item["narrative_ids"] = sorted(item_narrative_ids)

        state.set_stage_output("narratives", {"top_n": top_n, "clusters": clusters})
        return state
