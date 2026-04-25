"""YouTube research platform: concrete stage implementations and pipeline runner."""

from __future__ import annotations

import asyncio

from social_research_probe.platforms.base import BaseResearchPlatform, BaseStage
from social_research_probe.platforms.state import PipelineState
from social_research_probe.services.reporting.writer import write_final_report
from social_research_probe.services.sourcing.youtube import compute_engagement_metrics


class YouTubeFetchStage(BaseStage):
    """Fetch YouTube search results and compute engagement metrics."""

    def stage_name(self) -> str:
        return "fetch"

    async def execute(self, state: PipelineState) -> PipelineState:
        from social_research_probe.services.sourcing.youtube import YouTubeConnector

        empty: dict = {"items": [], "engagement_metrics": []}
        if not self._is_enabled(state):
            state.set_stage_output("fetch", empty)
            return state
        topic = state.inputs.get("topic", "")
        merged = state.inputs.get("merged_purpose")
        if merged is not None:
            from social_research_probe.utils.search.query import enrich_query
            search_topic = enrich_query(topic, merged.method)
        else:
            search_topic = topic
        connector = YouTubeConnector(state.platform_config)
        raw = await asyncio.to_thread(connector.find_by_topic, search_topic, connector.default_limits)
        items = await connector.fetch_item_details(raw)
        engagement_metrics = compute_engagement_metrics(items)
        state.set_stage_output("fetch", {"items": items, "engagement_metrics": engagement_metrics})
        return state


class YouTubeScoreStage(BaseStage):
    """Score and rank fetched items."""

    def stage_name(self) -> str:
        return "score"

    @staticmethod
    def _top_n_limit(state: PipelineState) -> int:
        return int(state.platform_config.get("enrich_top_n", 5))

    async def execute(self, state: PipelineState) -> PipelineState:
        from social_research_probe.technologies.scoring.combine import overall_score

        fetch = state.get_stage_output("fetch")
        items = fetch.get("items", [])
        limit = self._top_n_limit(state)
        fallback: dict = {"all_scored": items, "top_n": items[:limit]}
        if not self._is_enabled(state) or not items:
            state.set_stage_output("score", fallback)
            return state
        merged = state.inputs.get("merged_purpose")
        if merged is not None:
            from social_research_probe.config import load_active_config
            from social_research_probe.services.scoring.weights import resolve_scoring_weights
            weights = resolve_scoring_weights(load_active_config(), merged)
        else:
            weights = None
        try:
            scored = [
                {
                    **item,
                    "overall_score": overall_score(
                        trust=item.get("trust", 0.0),
                        trend=item.get("trend", 0.0),
                        opportunity=item.get("opportunity", 0.0),
                        weights=weights,
                    ),
                }
                for item in items
                if isinstance(item, dict)
            ]
        except Exception:
            scored = items
        top_n = scored[:limit]
        state.set_stage_output("score", {"all_scored": scored, "top_n": top_n})
        return state


class YouTubeTranscriptStage(BaseStage):
    """Fetch transcripts for top-N items."""

    def stage_name(self) -> str:
        return "transcript"

    async def execute(self, state: PipelineState) -> PipelineState:
        from social_research_probe.services.enriching.transcript import TranscriptService

        top_n = list(state.get_stage_output("score").get("top_n", []))
        if not self._is_enabled(state) or not top_n:
            state.set_stage_output("transcript", {"top_n": top_n})
            return state

        results = await TranscriptService().execute_batch(top_n)
        enriched = [
            {**item, "transcript": t}
            if (t := next((tr.output for tr in r.tech_results if tr.success and tr.output), None))
            else dict(item)
            for item, r in zip(top_n, results, strict=True)
            if isinstance(item, dict)
        ]
        state.set_stage_output("transcript", {"top_n": enriched})
        return state


class YouTubeSummaryStage(BaseStage):
    """Generate LLM summaries for top-N items."""

    def stage_name(self) -> str:
        return "summary"

    async def execute(self, state: PipelineState) -> PipelineState:
        from social_research_probe.services.enriching.summary import SummaryService

        top_n = list(state.get_stage_output("transcript").get("top_n", []))
        if not self._is_enabled(state) or not top_n:
            state.set_stage_output("summary", {"top_n": top_n})
            return state

        results = await SummaryService().execute_batch(top_n)
        final = [
            {**item, "summary": s}
            if (s := next((tr.output for tr in r.tech_results if tr.success and tr.output), None))
            else dict(item)
            for item, r in zip(top_n, results, strict=True)
        ]
        state.set_stage_output("summary", {"top_n": final})
        return state


class YouTubeCorroborateStage(BaseStage):
    """Corroborate claims in top-N items via configured search backends."""

    def stage_name(self) -> str:
        return "corroborate"

    async def execute(self, state: PipelineState) -> PipelineState:
        top_n = list(state.get_stage_output("summary").get("top_n", []))
        if not self._is_enabled(state) or not top_n:
            state.set_stage_output("corroborate", {"top_n": top_n})
            return state
        backends = self._resolve_backends()
        if not backends:
            state.set_stage_output("corroborate", {"top_n": top_n})
            return state

        from social_research_probe.services.corroborating.host import corroborate_item

        sem = asyncio.Semaphore(3)

        async def _run_one(item: dict) -> dict:
            async with sem:
                return await corroborate_item(item, backends)

        corroborated = list(await asyncio.gather(*(_run_one(item) for item in top_n)))
        state.set_stage_output("corroborate", {"top_n": corroborated})
        return state

    def _resolve_backends(self) -> list[str]:
        from social_research_probe.config import load_active_config
        from social_research_probe.services.corroborating.backends import auto_mode_backends
        from social_research_probe.services.corroborating.registry import get_backend
        from social_research_probe.utils.core.errors import ValidationError
        from social_research_probe.utils.display.fast_mode import (
            FAST_MODE_MAX_BACKENDS,
            fast_mode_enabled,
        )
        from social_research_probe.utils.display.progress import log

        cfg = load_active_config()
        configured = cfg.corroboration_backend
        if not cfg.service_enabled("corroboration") or configured == "none":
            return []
        candidates = auto_mode_backends(cfg) if configured == "auto" else (configured,)
        backends: list[str] = []
        for name in candidates:
            if not cfg.technology_enabled(name):
                continue
            if name == "llm_search" and not cfg.service_enabled("llm"):
                continue
            try:
                if get_backend(name).health_check():
                    backends.append(name)
            except ValidationError:
                pass
        if not backends:
            checked = ", ".join(candidates)
            log(
                f"[srp] corroboration: backend '{configured}' configured but no provider usable"
                f" (checked: {checked}). Hint: run 'srp config check-secrets --corroboration {configured}'."
            )
        return backends[:FAST_MODE_MAX_BACKENDS] if fast_mode_enabled() else backends


class YouTubeStatsStage(BaseStage):
    """Compute statistics on scored items."""

    def stage_name(self) -> str:
        return "stats"

    async def execute(self, state: PipelineState) -> PipelineState:
        from social_research_probe.services.analyzing.statistics import StatisticsService

        if not self._is_enabled(state):
            state.set_stage_output("stats", {"stats_summary": {}})
            return state

        top_n = list(state.get_stage_output("score").get("top_n", []))
        result = await StatisticsService().execute_one({"scored_items": top_n})
        stats_output = next((tr.output for tr in result.tech_results if tr.success), None)
        state.set_stage_output(
            "stats",
            {"stats_summary": stats_output if isinstance(stats_output, dict) else {}},
        )
        return state


class YouTubeChartsStage(BaseStage):
    """Render charts for scored items."""

    def stage_name(self) -> str:
        return "charts"

    async def execute(self, state: PipelineState) -> PipelineState:
        from social_research_probe.services.analyzing.charts import ChartsService

        if not self._is_enabled(state):
            state.set_stage_output("charts", {"chart_output": None, "chart_captions": [], "chart_takeaways": []})
            return state

        top_n = list(state.get_stage_output("score").get("top_n", []))
        result = await ChartsService().execute_one({"scored_items": top_n})
        chart_output = next((tr.output for tr in result.tech_results if tr.success), None)
        state.set_stage_output(
            "charts",
            {"chart_output": chart_output, "chart_captions": [], "chart_takeaways": []},
        )
        return state


class YouTubeSynthesisStage(BaseStage):
    """Generate LLM synthesis of all research findings."""

    def stage_name(self) -> str:
        return "synthesis"

    async def execute(self, state: PipelineState) -> PipelineState:
        from social_research_probe.services.llm.ensemble import multi_llm_prompt
        from social_research_probe.services.synthesizing.llm_contract import build_synthesis_prompt

        if not self._is_enabled(state):
            state.set_stage_output("synthesis", {"synthesis": ""})
            return state

        corroborate = state.get_stage_output("corroborate")
        score = state.get_stage_output("score")
        fetch = state.get_stage_output("fetch")
        stats = state.get_stage_output("stats")
        charts = state.get_stage_output("charts")
        top_n = list(corroborate.get("top_n") or score.get("top_n", []))

        synthesis_context: dict = {
            "top_n": top_n,
            "stats_results": stats.get("stats_summary", {}),
            "chart_results": charts.get("chart_output"),
            "items": fetch.get("items", []),
            "engagement_metrics": fetch.get("engagement_metrics", []),
            "topic": state.inputs.get("topic", ""),
        }
        try:
            synthesis_text = await multi_llm_prompt(build_synthesis_prompt(synthesis_context)) or ""
        except Exception:
            synthesis_text = ""

        state.set_stage_output("synthesis", {"synthesis": synthesis_text})
        return state


class YouTubeAssembleStage(BaseStage):
    """Assemble all stage outputs into the final research packet."""

    def stage_name(self) -> str:
        return "assemble"

    async def execute(self, state: PipelineState) -> PipelineState:
        if not self._is_enabled(state):
            return state

        from social_research_probe.services.synthesizing.evidence import summarize as summarize_evidence
        from social_research_probe.services.synthesizing.evidence import summarize_engagement_metrics
        from social_research_probe.services.synthesizing.formatter import build_packet

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

        warnings: list[str] = []
        from social_research_probe.config import load_active_config
        threshold = float(load_active_config().tunables.get("summary_divergence_threshold", 0.4))
        for item in top_n:
            divergence = item.get("summary_divergence") if isinstance(item, dict) else None
            if divergence is not None and divergence > threshold:
                title = (item.get("title") or "untitled")[:80]
                warnings.append(f"summary/transcript divergence on {title!r}: {divergence:.2f}")

        packet = build_packet(
            topic=topic,
            platform=platform,
            purpose_set=list(purpose_names),
            items_top_n=top_n,
            source_validation_summary={},
            platform_engagement_summary=summarize_engagement_metrics(engagement_metrics),
            evidence_summary=summarize_evidence(items, engagement_metrics, top_n),
            stats_summary=stats.get("stats_summary", {}),
            chart_captions=charts.get("chart_captions", []),
            chart_takeaways=charts.get("chart_takeaways", []),
            warnings=warnings,
        )

        state.set_stage_output("assemble", {"packet": packet})
        state.outputs["packet"] = packet
        return state


class YouTubeStructuredSynthesisStage(BaseStage):
    """Run structured LLM synthesis on the assembled packet and attach results."""

    def stage_name(self) -> str:
        return "structured_synthesis"

    async def execute(self, state: PipelineState) -> PipelineState:
        if not self._is_enabled(state):
            return state

        from social_research_probe.services.synthesizing.runner import attach_synthesis
        packet = state.outputs.get("packet", {})
        await asyncio.to_thread(attach_synthesis, packet)
        state.outputs["packet"] = packet
        return state


class YouTubeReportStage(BaseStage):
    """Write text and HTML research reports to disk."""

    def stage_name(self) -> str:
        return "report"

    async def execute(self, state: PipelineState) -> PipelineState:
        from social_research_probe.services.reporting.html import HtmlReportService

        if not self._is_enabled(state):
            return state

        packet = state.outputs.get("packet", {})
        allow_html = bool(state.platform_config.get("allow_html", True))
        report_path = write_final_report(packet, allow_html=allow_html)
        packet["report_path"] = report_path
        await HtmlReportService().execute_one({"packet": packet})
        state.outputs["packet"] = packet
        return state


class YouTubeNarrationStage(BaseStage):
    """Read evidence summary aloud via TTS."""

    def stage_name(self) -> str:
        return "narration"

    async def execute(self, state: PipelineState) -> PipelineState:
        from social_research_probe.services.reporting.audio import AudioReportService

        if not self._is_enabled(state):
            return state

        narration = str(state.outputs.get("packet", {}).get("evidence_summary", ""))
        if narration:
            await AudioReportService().execute_one({"text": narration})
        return state


class YouTubePipeline(BaseResearchPlatform):
    """Orchestrates all YouTube research stages and post-stage reports."""

    def stages(self) -> list[list[BaseStage]]:
        return [
            [YouTubeFetchStage()],
            [YouTubeScoreStage()],
            [YouTubeTranscriptStage(), YouTubeStatsStage(), YouTubeChartsStage()],
            [YouTubeSummaryStage()],
            [YouTubeCorroborateStage()],
            [YouTubeSynthesisStage()],
            [YouTubeAssembleStage()],
            [YouTubeStructuredSynthesisStage()],
            [YouTubeReportStage(), YouTubeNarrationStage()],
        ]

    async def run(self, state: PipelineState) -> PipelineState:
        for group in self.stages():
            if len(group) == 1:
                state = await group[0].execute(state)
            else:
                await asyncio.gather(*(s.execute(state) for s in group))
        return state
