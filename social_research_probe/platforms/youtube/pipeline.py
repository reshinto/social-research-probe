"""YouTube research platform: concrete stage implementations and pipeline runner."""

from __future__ import annotations

import asyncio

from social_research_probe.platforms import BaseResearchPlatform, BaseStage
from social_research_probe.platforms.state import PipelineState
from social_research_probe.services.reporting import write_final_report
from social_research_probe.utils.display.progress import log_with_time


def _channel_of(item: dict) -> str:
    return str(item.get("channel") or item.get("author_name") or "")


def _to_dict(item: object) -> dict | None:
    from social_research_probe.technologies.scoring import normalize_item

    return normalize_item(item)


def _normalize_items(raw_items: list) -> list[dict]:
    return [d for d in (_to_dict(it) for it in raw_items) if d is not None]


def _existing_class(item: dict) -> str:
    from social_research_probe.technologies.classifying import coerce_class

    return coerce_class(item.get("source_class"))


def _output_class(result) -> str:
    from social_research_probe.technologies.classifying import coerce_class

    for tr in result.tech_results:
        if tr.success and isinstance(tr.output, str):
            return coerce_class(tr.output)
    return "unknown"


def _title_overrides_to_commentary(item: dict) -> bool:
    from social_research_probe.technologies.classifying import (
        classify_by_title_signal,
    )

    return classify_by_title_signal(str(item.get("title") or "")) == "commentary"


def _enrich(item: dict, base_class: str) -> dict:
    enriched = dict(item)
    enriched["source_class"] = "commentary" if _title_overrides_to_commentary(item) else base_class
    return enriched


async def _resolve_class_for(service, item: dict, cache: dict[str, str]) -> str:
    existing = _existing_class(item)
    if existing != "unknown":
        return existing

    channel = _channel_of(item)
    if channel in cache:
        return cache[channel]

    result = await service.execute_one(item)
    resolved = _output_class(result)
    cache[channel] = resolved
    return resolved


def _empty_score_output(items: list, limit: int) -> dict:
    return {"all_scored": items, "top_n": items[:limit]}


def _merge_transcripts(top_n: list, results: list) -> list:
    return [
        (
            {**item, "transcript": t}
            if (
                t := next(
                    (tr.output for tr in r.tech_results if tr.success and tr.output),
                    None,
                )
            )
            else dict(item)
        )
        for item, r in zip(top_n, results, strict=True)
        if isinstance(item, dict)
    ]


def _merge_summaries(top_n: list, results: list) -> list:
    return [
        (
            {**item, "summary": s, "one_line_takeaway": s}
            if (
                s := next(
                    (tr.output for tr in r.tech_results if tr.success and tr.output),
                    None,
                )
            )
            else dict(item)
        )
        for item, r in zip(top_n, results, strict=True)
    ]


def _cap_corroboration_providers(providers: list[str]) -> list[str]:
    from social_research_probe.utils.display.fast_mode import (
        FAST_MODE_MAX_PROVIDERS,
        fast_mode_enabled,
    )

    return providers[:FAST_MODE_MAX_PROVIDERS] if fast_mode_enabled() else providers


def _merge_corroborations(top_n: list, results: list) -> list:
    return [
        (
            {**item, "corroboration": corr}
            if (
                corr := next(
                    (tr.output for tr in r.tech_results if tr.success and tr.output),
                    None,
                )
            )
            else dict(item)
        )
        for item, r in zip(top_n, results, strict=True)
        if isinstance(item, dict)
    ]


def _charts_empty_output() -> dict:
    return {"chart_outputs": [], "chart_captions": [], "chart_takeaways": []}


def _build_chart_output(chart_outputs: list) -> dict:
    return {
        "chart_outputs": chart_outputs,
        "chart_captions": [c.caption for c in chart_outputs],
        "chart_takeaways": [],
    }


async def _run_synthesis(context: dict) -> str:
    from social_research_probe.technologies.synthesizing.llm_contract import (
        build_synthesis_prompt,
    )
    from social_research_probe.utils.llm.ensemble import multi_llm_prompt

    try:
        return await multi_llm_prompt(build_synthesis_prompt(context)) or ""
    except Exception:
        return ""


def _collect_divergence_warnings(top_n: list, threshold: float) -> list[str]:
    warnings: list[str] = []
    for item in top_n:
        divergence = item.get("summary_divergence") if isinstance(item, dict) else None
        if divergence is not None and divergence > threshold:
            title = (item.get("title") or "untitled")[:80]
            warnings.append(f"summary/transcript divergence on {title!r}: {divergence:.2f}")
    return warnings


def _write_text_report(report: dict, allow_html: bool) -> str:
    return write_final_report(report, allow_html=allow_html)


async def _write_html_report(report: dict) -> None:
    from social_research_probe.services.reporting.html import HtmlReportService

    await HtmlReportService().execute_one({"report": report})


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
        from social_research_probe.services.sourcing.youtube import YouTubeSourcingService
        from social_research_probe.technologies.media_fetch import (
            YouTubeEngagementTech,
            YouTubeHydrateTech,
        )

        result = await YouTubeSourcingService(config).execute_one(search_topic)
        items: list = []
        engagement: list = []
        for tr in result.tech_results:
            if tr.tech_name == YouTubeHydrateTech.name and isinstance(tr.output, list):
                items = tr.output
            elif tr.tech_name == YouTubeEngagementTech.name and isinstance(tr.output, list):
                engagement = tr.output
        return items, engagement

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


class YouTubeClassifyStage(BaseStage):
    """Classify each fetched item's channel into a source_class enum value.

    Runs between fetch and score so downstream stages read a meaningful
    ``source_class`` instead of a hardcoded ``"unknown"``. Falls back to
    ``"unknown"`` when the service gate is off or the chosen provider
    returns no signal so the report still renders.
    """

    def stage_name(self) -> str:
        return "classify"

    async def _classify(self, items: list[dict]) -> list[dict]:
        from social_research_probe.services.classifying.source_class import (
            SourceClassService,
        )

        service = SourceClassService()
        cache: dict[str, str] = {}
        return [_enrich(item, await _resolve_class_for(service, item, cache)) for item in items]

    def _store_passthrough(self, state: PipelineState, raw_items: list) -> PipelineState:
        state.set_stage_output("classify", {"items": raw_items})
        return state

    def _store_classified(
        self, state: PipelineState, fetch: dict, classified: list[dict]
    ) -> PipelineState:
        fetch["items"] = classified
        state.set_stage_output("fetch", fetch)
        state.set_stage_output("classify", {"items": classified})
        return state

    @log_with_time("[srp] youtube/classify: execute")
    async def execute(self, state: PipelineState) -> PipelineState:
        fetch = state.get_stage_output("fetch")
        raw_items = list(fetch.get("items", []))

        if not self._is_enabled(state) or not raw_items:
            return self._store_passthrough(state, raw_items)

        items = _normalize_items(raw_items)
        if not items:
            return self._store_passthrough(state, raw_items)

        classified = await self._classify(items)
        return self._store_classified(state, fetch, classified)


class YouTubeScoreStage(BaseStage):
    """Score and rank fetched items."""

    def stage_name(self) -> str:
        return "score"

    def _top_n_limit(self, state: PipelineState) -> int:
        return int(state.platform_config.get("enrich_top_n", 5))

    def _resolve_purpose_scoring_weights(self, state: PipelineState):
        merged = state.inputs.get("merged_purpose")
        if merged is None:
            return None
        from social_research_probe.services.scoring import resolve_scoring_weights

        return resolve_scoring_weights(merged)

    @log_with_time("[srp] youtube/score: execute")
    async def execute(self, state: PipelineState) -> PipelineState:
        fetch = state.get_stage_output("fetch")
        items = fetch.get("items", [])
        limit = self._top_n_limit(state)
        if not self._is_enabled(state) or not items:
            state.set_stage_output("score", _empty_score_output(items, limit))
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

    @log_with_time("[srp] youtube/transcript: execute")
    async def execute(self, state: PipelineState) -> PipelineState:
        from social_research_probe.services.enriching.transcript import (
            TranscriptService,
        )

        top_n = list(state.get_stage_output("score").get("top_n", []))
        if not self._is_enabled(state) or not top_n:
            state.set_stage_output("transcript", {"top_n": top_n})
            return state
        results = await TranscriptService().execute_batch(top_n)
        enriched = _merge_transcripts(top_n, results)
        state.set_stage_output("transcript", {"top_n": enriched})
        return state


class YouTubeSummaryStage(BaseStage):
    """Generate LLM summaries for top-N items."""

    def stage_name(self) -> str:
        return "summary"

    @log_with_time("[srp] youtube/summary: execute")
    async def execute(self, state: PipelineState) -> PipelineState:
        from social_research_probe.services.enriching.summary import SummaryService

        top_n = list(state.get_stage_output("transcript").get("top_n", []))
        if not self._is_enabled(state) or not top_n:
            state.set_stage_output("summary", {"top_n": top_n})
            return state
        results = await SummaryService().execute_batch(top_n)
        final = _merge_summaries(top_n, results)
        state.set_stage_output("summary", {"top_n": final})
        return state


class YouTubeCorroborateStage(BaseStage):
    """Corroborate claims in top-N items via configured search providers."""

    def stage_name(self) -> str:
        return "corroborate"

    def _select_corroboration_providers(self) -> list[str]:
        from social_research_probe.config import load_active_config
        from social_research_probe.services.corroborating import (
            select_healthy_providers,
        )
        from social_research_probe.utils.display.progress import log

        configured = load_active_config().corroboration_provider
        providers, candidates = select_healthy_providers(configured)
        if not providers and candidates:
            checked = ", ".join(candidates)
            log(
                f"[srp] corroboration: provider '{configured}' configured but no provider usable"
                f" (checked: {checked}). Hint: run 'srp config check-secrets --corroboration {configured}'."
            )
        return _cap_corroboration_providers(providers)

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

        from social_research_probe.services.corroborating.corroborate import (
            CorroborationService,
        )

        results = await CorroborationService(providers).execute_batch(top_n)
        corroborated = _merge_corroborations(top_n, results)

        state.set_stage_output("corroborate", {"top_n": corroborated})
        return state


class YouTubeStatsStage(BaseStage):
    """Compute statistics on scored items."""

    def stage_name(self) -> str:
        return "stats"

    @log_with_time("[srp] youtube/stats: execute")
    async def execute(self, state: PipelineState) -> PipelineState:
        from social_research_probe.services.analyzing.statistics import (
            StatisticsService,
        )

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

    def _scored_dataset(self, state: PipelineState) -> list:
        score = state.get_stage_output("score")
        return list(score.get("all_scored") or score.get("top_n", []))

    async def _render_outputs(self, items: list) -> list:
        from social_research_probe.services.analyzing.charts import ChartsService

        result = await ChartsService().execute_one({"scored_items": items})
        for tr in result.tech_results:
            if tr.success and isinstance(tr.output, list):
                return tr.output
        return []

    @log_with_time("[srp] youtube/charts: execute")
    async def execute(self, state: PipelineState) -> PipelineState:
        if not self._is_enabled(state):
            state.set_stage_output("charts", _charts_empty_output())
            return state
        items = self._scored_dataset(state)
        outputs = await self._render_outputs(items)
        state.set_stage_output("charts", _build_chart_output(outputs))
        return state


class YouTubeSynthesisStage(BaseStage):
    """Generate LLM synthesis of all research findings."""

    def stage_name(self) -> str:
        return "synthesis"

    def _build_synthesis_context(self, state: PipelineState) -> dict:
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

    @log_with_time("[srp] youtube/synthesis: execute")
    async def execute(self, state: PipelineState) -> PipelineState:
        if not self._is_enabled(state):
            state.set_stage_output("synthesis", {"synthesis": ""})
            return state
        context = self._build_synthesis_context(state)
        synthesis_text = await _run_synthesis(context)
        state.set_stage_output("synthesis", {"synthesis": synthesis_text})
        return state


class YouTubeAssembleStage(BaseStage):
    """Assemble all stage outputs into the final research report."""

    def stage_name(self) -> str:
        return "assemble"

    def _build_source_validation_summary(self, top_n: list) -> dict:
        from collections import Counter

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
        return {
            "validated": verdict_counts.get("validated", 0),
            "partially": verdict_counts.get("partially", 0),
            "unverified": verdict_counts.get("unverified", 0),
            "low_trust": verdict_counts.get("low_trust", 0),
            "primary": class_counts.get("primary", 0),
            "secondary": class_counts.get("secondary", 0),
            "commentary": class_counts.get("commentary", 0),
            "notes": "",
        }

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
        from social_research_probe.services.synthesizing.synthesis.helpers.evidence import (
            summarize as summarize_evidence,
        )
        from social_research_probe.services.synthesizing.synthesis.helpers.evidence import (
            summarize_engagement_metrics,
        )
        from social_research_probe.utils.report.formatter import (
            build_report,
        )

        return build_report(
            topic=topic,
            platform=platform,
            purpose_set=list(purpose_names),
            items_top_n=top_n,
            source_validation_summary=self._build_source_validation_summary(top_n),
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
        warnings = _collect_divergence_warnings(top_n, threshold)

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

        from social_research_probe.services.synthesizing.synthesis.runner import (
            attach_synthesis,
        )

        report = state.outputs.get("report", {})
        await asyncio.to_thread(attach_synthesis, report)
        state.outputs["report"] = report
        return state


class YouTubeReportStage(BaseStage):
    """Write text and HTML research reports to disk."""

    def stage_name(self) -> str:
        return "report"

    @log_with_time("[srp] youtube/report: execute")
    async def execute(self, state: PipelineState) -> PipelineState:
        if not self._is_enabled(state):
            return state

        report = state.outputs.get("report", {})
        allow_html = bool(state.platform_config.get("allow_html", True))
        report_path = _write_text_report(report, allow_html)
        report["report_path"] = report_path
        await _write_html_report(report)
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
            [YouTubeClassifyStage()],
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
                state = await group[0].run(state)
            else:
                await asyncio.gather(*(s.run(state) for s in group))
        return state
