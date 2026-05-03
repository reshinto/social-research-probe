"""YouTubeAssembleStage implementation."""

from __future__ import annotations

from social_research_probe.platforms import BaseStage
from social_research_probe.platforms.state import PipelineState
from social_research_probe.utils.display.progress import log


class YouTubeAssembleStage(BaseStage):
    """Assemble all stage outputs into the final research report.

    Examples:
        Input:
            YouTubeAssembleStage
        Output:
            YouTubeAssembleStage()
    """

    @property
    def stage_name(self) -> str:
        """Return the `assemble` stage key used by config and PipelineState.

        Config, cache, and PipelineState all key off this value, so it is kept beside the stage
        implementation that owns it.

        Returns:
            The configured stage name setting.

        Examples:
            Input:
                stage.stage_name
            Output:
                "assemble"
        """
        return "assemble"

    def _build_source_validation_summary(self, top_n: list) -> dict:
        """Build build source validation summary in the shape consumed by the next project step.

        The report pipeline needs a predictable text payload even when transcripts or summaries are
        missing.

        Args:
            top_n: Ordered source items being carried through the current pipeline step.

        Returns:
            Dictionary with stable keys consumed by downstream project code.

        Examples:
            Input:
                _build_source_validation_summary(
                    top_n=[{"title": "Example", "url": "https://youtu.be/demo"}],
                )
            Output:
                {"enabled": True}
        """
        from collections import Counter

        from social_research_probe.config import load_active_config

        cfg = load_active_config()
        debug = cfg.debug_enabled("pipeline")
        if debug:
            log(f"[srp] assemble: _build_source_validation_summary len(top_n)={len(top_n)}")

        verdict_map = {"supported": "validated", "refuted": "low_trust"}
        verdict_counts: Counter[str] = Counter()
        class_counts: Counter[str] = Counter()
        for item in top_n:
            sc = item.get("source_class", "unknown")
            if sc in ("primary", "secondary", "commentary"):
                class_counts[sc] += 1
            corr = item.get("corroboration", {})
            raw = corr.get("aggregate_verdict", "inconclusive") if corr else "inconclusive"
            mapped = verdict_map.get(raw, "unverified")
            verdict_counts[mapped] += 1
        result = {
            "validated": verdict_counts.get("validated", 0),
            "partially": verdict_counts.get("partially", 0),
            "unverified": verdict_counts.get("unverified", 0),
            "low_trust": verdict_counts.get("low_trust", 0),
            "primary": class_counts.get("primary", 0),
            "secondary": class_counts.get("secondary", 0),
            "commentary": class_counts.get("commentary", 0),
            "notes": "",
        }
        if debug:
            log(f"[srp] assemble: source_validation_summary={result}")
        return result

    def _compose_research_report_data(
        self,
        topic: str,
        platform: str,
        purpose_names: list,
        top_n: list,
        items: list,
        engagement_metrics: list,
        stats_summary: dict,
        chart_captions: list,
        chart_takeaways: list,
        warnings: list[str],
    ) -> dict:
        """Build the small payload that carries source_validation_summary through this workflow.

        The YouTube pipeline carries a shared PipelineState; this helper keeps this stage's input and
        output contract explicit for the next stage.

        Args:
            topic: Research topic text or existing topic list used for classification and suggestions.
            platform: Platform name, such as youtube or all, used to select config and pipeline
                      behavior.
            purpose_names: Purpose name or purpose definitions that shape the research goal.
            top_n: Ordered source items being carried through the current pipeline step.
            items: Ordered source items being carried through the current pipeline step.
            engagement_metrics: Engagement metric dictionary used to build report evidence and warnings.
            stats_summary: Statistical summary records shown in the report.
            chart_captions: Chart captions shown next to rendered chart artifacts.
            chart_takeaways: Chart takeaways value that changes the behavior described by this
                             helper.
            warnings: Warning or penalty records that explain reduced evidence quality.

        Returns:
            Dictionary with stable keys consumed by downstream project code.

        Examples:
            Input:
                _compose_research_report_data(
                    topic="AI safety",
                    platform="AI safety",
                    purpose_names=("Opportunity Map",),
                    top_n=[{"title": "Example", "url": "https://youtu.be/demo"}],
                    items=[{"title": "Example", "url": "https://youtu.be/demo"}],
                    engagement_metrics={"views": 1200, "likes": 80},
                    stats_summary={"enabled": True},
                    chart_captions=["AI safety"],
                    chart_takeaways=["AI safety"],
                    warnings=["Transcript unavailable"],
                )
            Output:
                {"enabled": True}
        """
        from social_research_probe.services.synthesizing.synthesis.helpers.evidence import (
            summarize as summarize_evidence,
        )
        from social_research_probe.services.synthesizing.synthesis.helpers.evidence import (
            summarize_engagement_metrics,
        )
        from social_research_probe.utils.report.formatter import build_report

        svs = self._build_source_validation_summary(top_n)
        report = build_report(
            topic=topic,
            platform=platform,
            purpose_set=list(purpose_names),
            items_top_n=top_n,
            source_validation_summary=svs,
            platform_engagement_summary=summarize_engagement_metrics(engagement_metrics),
            evidence_summary=summarize_evidence(items, engagement_metrics, top_n),
            stats_summary=stats_summary,
            chart_captions=chart_captions,
            chart_takeaways=chart_takeaways,
            warnings=warnings,
        )
        reported_svs = report.get("source_validation_summary", {})
        verdict_keys = ("validated", "partially", "unverified", "low_trust")
        if top_n and all(reported_svs.get(k, 0) == 0 for k in verdict_keys):
            log(
                "[srp] assemble: WARNING all validation counts zero despite non-empty top_n — recomputing"
            )
            report["source_validation_summary"] = self._build_source_validation_summary(top_n)
        return report

    async def execute(self, state: PipelineState) -> PipelineState:
        """Run the YouTube assemble stage and publish its PipelineState output.

        The YouTube assemble stage reads the state built so far and publishes the smallest output later
        stages need.

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
        from social_research_probe.utils.pipeline.helpers import collect_divergence_warnings

        if not self._is_enabled(state):
            return state

        fetch = state.get_stage_output("fetch")
        corroborate = state.get_stage_output("corroborate")
        score = state.get_stage_output("score")
        stats = state.get_stage_output("stats")
        charts = state.get_stage_output("charts")

        items = fetch.get("items", [])
        engagement_metrics = fetch.get("engagement_metrics", [])
        top_n = corroborate.get("top_n") or score.get("top_n", [])

        cmd = state.cmd
        topic = state.inputs.get("topic", "")
        platform = getattr(cmd, "platform", "youtube")
        purpose_names = state.inputs.get("purpose_names", [])

        from social_research_probe.config import load_active_config

        threshold = float(load_active_config().tunables.get("summary_divergence_threshold", 0.4))
        warnings = collect_divergence_warnings(top_n, threshold)

        report = self._compose_research_report_data(
            topic=topic,
            platform=platform,
            purpose_names=purpose_names,
            top_n=top_n,
            items=items,
            engagement_metrics=engagement_metrics,
            stats_summary=stats.get("stats_summary", {}),
            chart_captions=charts.get("chart_captions", []),
            chart_takeaways=charts.get("chart_takeaways", []),
            warnings=warnings,
        )

        narratives_output = state.get_stage_output("narratives")
        report["narratives"] = narratives_output.get("clusters", [])

        state.set_stage_output("assemble", {"report": report})
        state.outputs["report"] = report
        return state
