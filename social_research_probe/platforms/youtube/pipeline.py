"""YouTube research platform: concrete stage implementations and pipeline runner."""

from __future__ import annotations

import asyncio

from social_research_probe.platforms.base import BaseResearchPlatform, BaseStage
from social_research_probe.platforms.state import PipelineState
from social_research_probe.services.reporting import write_final_report
from social_research_probe.utils.display.progress import log_with_time


class YouTubeFetchStage(BaseStage):
    """Fetch YouTube search results and compute engagement metrics."""

    def stage_name(self) -> str:
        return "fetch"

    def _resolve_search_topic(self, state: PipelineState) -> str:
        topic = state.inputs.get("topic", "")
        merged = state.inputs.get("merged_purpose")
        if merged is not None:
            from social_research_probe.utils.search.query import enrich_query

            return enrich_query(topic, merged.method)
        return topic

    async def _fetch_items(self, search_topic: str, config: dict) -> tuple[list, list]:
        from social_research_probe.services.sourcing import youtube as yt_sourcing

        return await yt_sourcing.run_youtube_sourcing(search_topic, config)

    @log_with_time("[srp] youtube/fetch: execute")
    async def execute(self, state: PipelineState) -> PipelineState:
        empty: dict = {"items": [], "engagement_metrics": []}
        if not self._is_enabled(state):
            state.set_stage_output("fetch", empty)
            return state
        search_topic = self._resolve_search_topic(state)
        items, engagement_metrics = await self._fetch_items(search_topic, state.platform_config)
        state.set_stage_output("fetch", {"items": items, "engagement_metrics": engagement_metrics})
        return state


class YouTubeScoreStage(BaseStage):
    """Score and rank fetched items."""

    def stage_name(self) -> str:
        return "score"

    @staticmethod
    def _top_n_limit(state: PipelineState) -> int:
        return int(state.platform_config.get("enrich_top_n", 5))

    @staticmethod
    def _resolve_purpose_scoring_weights(state: PipelineState):
        merged = state.inputs.get("merged_purpose")
        if merged is None:
            return None
        from social_research_probe.config import load_active_config
        from social_research_probe.services.scoring import resolve_scoring_weights

        return resolve_scoring_weights(load_active_config(), merged)

    @staticmethod
    def _empty_score_output(items: list, limit: int) -> dict:
        return {"all_scored": items, "top_n": items[:limit]}

    @log_with_time("[srp] youtube/score: execute")
    async def execute(self, state: PipelineState) -> PipelineState:
        fetch = state.get_stage_output("fetch")
        items = fetch.get("items", [])
        limit = self._top_n_limit(state)
        if not self._is_enabled(state) or not items:
            state.set_stage_output("score", self._empty_score_output(items, limit))
            return state
        weights = self._resolve_purpose_scoring_weights(state)

        from social_research_probe.services.scoring.score import ScoringService

        data = {
            "items": items,
            "engagement_metrics": fetch.get("engagement_metrics", []),
            "weights": weights,
        }
        result = await ScoringService().execute_one(data)

        scored = []
        for tr in result.tech_results:
            if tr.success and isinstance(tr.output, list):
                scored = tr.output
                break

        state.set_stage_output("score", {"all_scored": scored, "top_n": scored[:limit]})
        return state


class YouTubeTranscriptStage(BaseStage):
    """Fetch transcripts for top-N items."""

    def stage_name(self) -> str:
        return "transcript"

    @staticmethod
    def _merge_transcripts(top_n: list, results: list) -> list:
        return [
            {**item, "transcript": t}
            if (t := next((tr.output for tr in r.tech_results if tr.success and tr.output), None))
            else dict(item)
            for item, r in zip(top_n, results, strict=True)
            if isinstance(item, dict)
        ]

    @log_with_time("[srp] youtube/transcript: execute")
    async def execute(self, state: PipelineState) -> PipelineState:
        from social_research_probe.services.enriching.transcript import TranscriptService

        top_n = list(state.get_stage_output("score").get("top_n", []))
        if not self._is_enabled(state) or not top_n:
            state.set_stage_output("transcript", {"top_n": top_n})
            return state
        results = await TranscriptService().execute_batch(top_n)
        enriched = self._merge_transcripts(top_n, results)
        state.set_stage_output("transcript", {"top_n": enriched})
        return state


class YouTubeSummaryStage(BaseStage):
    """Generate LLM summaries for top-N items."""

    def stage_name(self) -> str:
        return "summary"

    @staticmethod
    def _merge_summaries(top_n: list, results: list) -> list:
        return [
            {**item, "summary": s, "one_line_takeaway": s}
            if (s := next((tr.output for tr in r.tech_results if tr.success and tr.output), None))
            else dict(item)
            for item, r in zip(top_n, results, strict=True)
        ]

    @log_with_time("[srp] youtube/summary: execute")
    async def execute(self, state: PipelineState) -> PipelineState:
        from social_research_probe.services.enriching.summary import SummaryService

        top_n = list(state.get_stage_output("transcript").get("top_n", []))
        if not self._is_enabled(state) or not top_n:
            state.set_stage_output("summary", {"top_n": top_n})
            return state
        results = await SummaryService().execute_batch(top_n)
        final = self._merge_summaries(top_n, results)
        state.set_stage_output("summary", {"top_n": final})
        return state


class YouTubeCorroborateStage(BaseStage):
    """Corroborate claims in top-N items via configured search providers."""

    def stage_name(self) -> str:
        return "corroborate"

    @staticmethod
    def _list_corroboration_provider_candidates(cfg, configured: str) -> tuple:
        from social_research_probe.services.corroborating import auto_mode_providers

        return auto_mode_providers(cfg) if configured == "auto" else (configured,)

    @staticmethod
    def _select_healthy_corroboration_providers(candidates: tuple, cfg) -> list[str]:
        from social_research_probe.services.corroborating import get_provider
        from social_research_probe.utils.core.errors import ValidationError

        providers: list[str] = []
        for name in candidates:
            if not cfg.technology_enabled(name):
                continue
            if name == "llm_search" and not cfg.service_enabled("llm"):
                continue
            try:
                if get_provider(name).health_check():
                    providers.append(name)
            except ValidationError:
                pass
        return providers

    @staticmethod
    def _cap_corroboration_providers_in_fast_mode(providers: list[str]) -> list[str]:
        from social_research_probe.utils.display.fast_mode import (
            FAST_MODE_MAX_PROVIDERS,
            fast_mode_enabled,
        )

        return providers[:FAST_MODE_MAX_PROVIDERS] if fast_mode_enabled() else providers

    def _select_corroboration_providers(self) -> list[str]:
        from social_research_probe.config import load_active_config
        from social_research_probe.utils.display.progress import log

        cfg = load_active_config()
        configured = cfg.corroboration_provider
        if not cfg.service_enabled("corroboration") or configured == "none":
            return []
        candidates = self._list_corroboration_provider_candidates(cfg, configured)
        providers = self._select_healthy_corroboration_providers(candidates, cfg)
        if not providers:
            checked = ", ".join(candidates)
            log(
                f"[srp] corroboration: provider '{configured}' configured but no provider usable"
                f" (checked: {checked}). Hint: run 'srp config check-secrets --corroboration {configured}'."
            )
        return self._cap_corroboration_providers_in_fast_mode(providers)

    @staticmethod
    def _merge_corroborations(top_n: list, results: list) -> list:
        return [
            {**item, "corroboration": corr}
            if (
                corr := next((tr.output for tr in r.tech_results if tr.success and tr.output), None)
            )
            else dict(item)
            for item, r in zip(top_n, results, strict=True)
            if isinstance(item, dict)
        ]

    @log_with_time("[srp] youtube/corroborate: execute")
    async def execute(self, state: PipelineState) -> PipelineState:
        top_n = list(state.get_stage_output("summary").get("top_n", []))
        if not self._is_enabled(state) or not top_n:
            state.set_stage_output("corroborate", {"top_n": top_n})
            return state
        providers = self._select_corroboration_providers()
        if not providers:
            state.set_stage_output("corroborate", {"top_n": top_n})
            return state

        from social_research_probe.services.corroborating.corroborate import CorroborationService

        results = await CorroborationService(providers).execute_batch(top_n)
        corroborated = self._merge_corroborations(top_n, results)

        state.set_stage_output("corroborate", {"top_n": corroborated})
        return state


class YouTubeStatsStage(BaseStage):
    """Compute statistics on scored items."""

    def stage_name(self) -> str:
        return "stats"

    @log_with_time("[srp] youtube/stats: execute")
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

    @staticmethod
    def _empty_output() -> dict:
        return {"chart_outputs": [], "chart_captions": [], "chart_takeaways": []}

    @staticmethod
    def _scored_dataset(state: PipelineState) -> list:
        score = state.get_stage_output("score")
        return list(score.get("all_scored") or score.get("top_n", []))

    @staticmethod
    async def _render_outputs(items: list) -> list:
        from social_research_probe.services.analyzing.charts import ChartsService

        result = await ChartsService().execute_one({"scored_items": items})
        for tr in result.tech_results:
            if tr.success and isinstance(tr.output, list):
                return tr.output
        return []

    @staticmethod
    def _build_output(chart_outputs: list) -> dict:
        return {
            "chart_outputs": chart_outputs,
            "chart_captions": [c.caption for c in chart_outputs],
            "chart_takeaways": [],
        }

    @log_with_time("[srp] youtube/charts: execute")
    async def execute(self, state: PipelineState) -> PipelineState:
        if not self._is_enabled(state):
            state.set_stage_output("charts", self._empty_output())
            return state
        items = self._scored_dataset(state)
        outputs = await self._render_outputs(items)
        state.set_stage_output("charts", self._build_output(outputs))
        return state


class YouTubeSynthesisStage(BaseStage):
    """Generate LLM synthesis of all research findings."""

    def stage_name(self) -> str:
        return "synthesis"

    @staticmethod
    def _build_synthesis_context(state: PipelineState) -> dict:
        corroborate = state.get_stage_output("corroborate")
        score = state.get_stage_output("score")
        fetch = state.get_stage_output("fetch")
        stats = state.get_stage_output("stats")
        charts = state.get_stage_output("charts")
        top_n = list(corroborate.get("top_n") or score.get("top_n", []))
        return {
            "top_n": top_n,
            "stats_results": stats.get("stats_summary", {}),
            "chart_results": charts.get("chart_outputs", []),
            "items": fetch.get("items", []),
            "engagement_metrics": fetch.get("engagement_metrics", []),
            "topic": state.inputs.get("topic", ""),
        }

    @staticmethod
    async def _run_synthesis(context: dict) -> str:
        from social_research_probe.services.llm.ensemble import multi_llm_prompt
        from social_research_probe.services.synthesizing.llm_contract import build_synthesis_prompt

        try:
            return await multi_llm_prompt(build_synthesis_prompt(context)) or ""
        except Exception:
            return ""

    @log_with_time("[srp] youtube/synthesis: execute")
    async def execute(self, state: PipelineState) -> PipelineState:
        if not self._is_enabled(state):
            state.set_stage_output("synthesis", {"synthesis": ""})
            return state
        context = self._build_synthesis_context(state)
        synthesis_text = await self._run_synthesis(context)
        state.set_stage_output("synthesis", {"synthesis": synthesis_text})
        return state


class YouTubeAssembleStage(BaseStage):
    """Assemble all stage outputs into the final research report."""

    def stage_name(self) -> str:
        return "assemble"

    @staticmethod
    def _collect_divergence_warnings(top_n: list, threshold: float) -> list[str]:
        warnings: list[str] = []
        for item in top_n:
            divergence = item.get("summary_divergence") if isinstance(item, dict) else None
            if divergence is not None and divergence > threshold:
                title = (item.get("title") or "untitled")[:80]
                warnings.append(f"summary/transcript divergence on {title!r}: {divergence:.2f}")
        return warnings

    @staticmethod
    def _compose_research_report_data(
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
        from social_research_probe.services.synthesizing.evidence import (
            summarize as summarize_evidence,
        )
        from social_research_probe.services.synthesizing.evidence import (
            summarize_engagement_metrics,
        )
        from social_research_probe.services.synthesizing.formatter import build_report

        return build_report(
            topic=topic,
            platform=platform,
            purpose_set=list(purpose_names),
            items_top_n=top_n,
            source_validation_summary={},
            platform_engagement_summary=summarize_engagement_metrics(engagement_metrics),
            evidence_summary=summarize_evidence(items, engagement_metrics, top_n),
            stats_summary=stats_summary,
            chart_captions=chart_captions,
            chart_takeaways=chart_takeaways,
            warnings=warnings,
        )

    @log_with_time("[srp] youtube/assemble: execute")
    async def execute(self, state: PipelineState) -> PipelineState:
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
        warnings = self._collect_divergence_warnings(top_n, threshold)

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

        state.set_stage_output("assemble", {"report": report})
        state.outputs["report"] = report
        return state


class YouTubeStructuredSynthesisStage(BaseStage):
    """Run structured LLM synthesis on the assembled report and attach results."""

    def stage_name(self) -> str:
        return "structured_synthesis"

    @log_with_time("[srp] youtube/structured_synthesis: execute")
    async def execute(self, state: PipelineState) -> PipelineState:
        if not self._is_enabled(state):
            return state

        from social_research_probe.services.synthesizing.runner import attach_synthesis

        report = state.outputs.get("report", {})
        await asyncio.to_thread(attach_synthesis, report)
        state.outputs["report"] = report
        return state


class YouTubeReportStage(BaseStage):
    """Write text and HTML research reports to disk."""

    def stage_name(self) -> str:
        return "report"

    @staticmethod
    def _write_text_report(report: dict, allow_html: bool) -> str:
        return write_final_report(report, allow_html=allow_html)

    @staticmethod
    async def _write_html_report(report: dict) -> None:
        from social_research_probe.services.reporting.html import HtmlReportService

        await HtmlReportService().execute_one({"report": report})

    @log_with_time("[srp] youtube/report: execute")
    async def execute(self, state: PipelineState) -> PipelineState:
        if not self._is_enabled(state):
            return state

        report = state.outputs.get("report", {})
        allow_html = bool(state.platform_config.get("allow_html", True))
        report_path = self._write_text_report(report, allow_html)
        report["report_path"] = report_path
        await self._write_html_report(report)
        state.outputs["report"] = report
        return state


class YouTubeNarrationStage(BaseStage):
    """Read evidence summary aloud via TTS."""

    def stage_name(self) -> str:
        return "narration"

    @log_with_time("[srp] youtube/narration: execute")
    async def execute(self, state: PipelineState) -> PipelineState:
        from social_research_probe.services.reporting.audio import AudioReportService

        if not self._is_enabled(state):
            return state

        narration = str(state.outputs.get("report", {}).get("evidence_summary", ""))
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

    @log_with_time("[srp] youtube/pipeline: run")
    async def run(self, state: PipelineState) -> PipelineState:
        for group in self.stages():
            if len(group) == 1:
                state = await group[0].execute(state)
            else:
                await asyncio.gather(*(s.execute(state) for s in group))
        return state
