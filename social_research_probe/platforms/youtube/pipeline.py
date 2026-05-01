"""YouTube research platform: concrete stage implementations and pipeline runner."""

from __future__ import annotations

import asyncio
from typing import ClassVar

from social_research_probe.platforms import BaseResearchPlatform, BaseStage
from social_research_probe.platforms.state import PipelineState
from social_research_probe.utils.display.progress import log, log_with_time
from social_research_probe.utils.pipeline.helpers import dict_items, first_tech_output


class YouTubeFetchStage(BaseStage):
    """Fetch YouTube search results and compute engagement metrics."""

    disable_cache_for_technologies: ClassVar[list[str]] = ["youtube_search", "youtube_hydrate"]

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

        result = (await YouTubeSourcingService(config).execute_batch([search_topic]))[0]
        items: list = []
        engagement: list = []
        for tr in result.tech_results:
            if tr.tech_name == "youtube_hydrate" and isinstance(tr.output, list):
                items = tr.output
            elif tr.tech_name == "youtube_engagement" and isinstance(tr.output, list):
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

    async def _classify(self, items: list) -> list[dict]:
        from social_research_probe.services.classifying.source_class import SourceClassService
        from social_research_probe.utils.core.classifying import (
            classify_by_title_signal,
            coerce_class,
        )
        from social_research_probe.utils.pipeline.helpers import normalize_item

        def _output_class(result) -> str:
            for tr in result.tech_results:
                if tr.success and isinstance(tr.output, dict):
                    return coerce_class(tr.output.get("source_class"))
            return "unknown"

        def _title_override(item: dict) -> bool:
            return classify_by_title_signal(str(item.get("title") or "")) == "commentary"

        normalized = [d for d in (normalize_item(it) for it in items) if d is not None]
        if not normalized:
            return list(items)

        service = SourceClassService()
        channel_cache: dict[str, str] = {}
        classified: list[dict] = []
        pending: list[dict] = []
        pending_channels: list[str] = []
        pending_seen: set[str] = set()
        for item in normalized:
            existing = coerce_class(item.get("source_class"))
            channel = str(item.get("channel") or item.get("author_name") or "")
            if existing != "unknown":
                source_class = existing
            elif channel in pending_seen:
                source_class = "unknown"
            else:
                pending.append(item)
                pending_channels.append(channel)
                pending_seen.add(channel)
                source_class = "unknown"
            enriched = dict(item)
            enriched["source_class"] = "commentary" if _title_override(item) else source_class
            classified.append(enriched)
        if pending:
            results = await service.execute_batch(pending)
            resolved_by_channel = {
                channel: _output_class(result)
                for channel, result in zip(pending_channels, results, strict=True)
            }
            channel_cache.update(resolved_by_channel)
            for item in classified:
                if item.get("source_class") == "unknown":
                    channel = str(item.get("channel") or item.get("author_name") or "")
                    item["source_class"] = (
                        "commentary"
                        if _title_override(item)
                        else channel_cache.get(channel, "unknown")
                    )
        return classified

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

        classified = await self._classify(raw_items)
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

        if not self._is_enabled(state):
            state.set_stage_output("score", {"all_scored": items, "top_n": items[:limit]})
            return state

        weights = self._resolve_purpose_scoring_weights(state)

        from social_research_probe.services.scoring.score import ScoringService

        service = ScoringService()
        result = (
            await service.execute_batch(
                [
                    {
                        "items": items,
                        "engagement_metrics": fetch.get("engagement_metrics", []),
                        "weights": weights,
                        "limit": limit,
                    }
                ]
            )
        )[0]
        score_output = next(
            (tr.output for tr in result.tech_results if tr.success and isinstance(tr.output, dict)),
            {"all_scored": [], "top_n": []},
        )
        state.set_stage_output("score", score_output)
        return state


class YouTubeTranscriptStage(BaseStage):
    """Fetch transcripts for top-N items."""

    def stage_name(self) -> str:
        return "transcript"

    @log_with_time("[srp] youtube/transcript: execute")
    async def execute(self, state: PipelineState) -> PipelineState:
        from social_research_probe.services.enriching.transcript import TranscriptService

        top_n = list(state.get_stage_output("score").get("top_n", []))
        if not self._is_enabled(state):
            # Preserve the ranked item list while marking transcript evidence as intentionally absent.
            # Downstream stages can then distinguish a configured skip from a provider failure.
            disabled = [
                {**it, "transcript_status": "disabled"} if isinstance(it, dict) else it
                for it in top_n
            ]
            state.set_stage_output("transcript", {"top_n": disabled})
            return state
        if not top_n:
            state.set_stage_output("transcript", {"top_n": top_n})
            return state
        service = TranscriptService()
        transcript_inputs = [item for item in top_n if isinstance(item, dict)]
        results = await service.execute_batch(transcript_inputs)
        enriched: list[dict] = []
        for result in results:
            item = next(
                (tr.output for tr in result.tech_results if isinstance(tr.output, dict)),
                None,
            )
            if item:
                enriched.append(item)
        state.set_stage_output("transcript", {"top_n": enriched})
        return state


class YouTubeCommentsStage(BaseStage):
    """Fetch YouTube comments for top-N items."""

    def stage_name(self) -> str:
        return "comments"

    @log_with_time("[srp] youtube/comments: execute")
    async def execute(self, state: PipelineState) -> PipelineState:
        from social_research_probe.services.enriching.comments import CommentsService

        top_n = list(state.get_stage_output("transcript").get("top_n", []))
        if not self._is_enabled(state):
            self._set_comments_output(state, self._disabled_items(top_n))
            return state
        if not top_n:
            self._set_comments_output(state, top_n)
            return state

        available_items = dict_items(top_n)
        fetch_items = self._fetch_items(available_items, state)
        inputs = self._service_inputs(fetch_items, state)
        results = await CommentsService().execute_batch(inputs)
        enriched = self._enriched_items(fetch_items, results)
        enriched.extend(self._not_attempted_items(available_items, state))
        self._set_comments_output(state, enriched)
        return state

    def _set_comments_output(self, state: PipelineState, top_n: list) -> None:
        state.set_stage_output("comments", {"top_n": top_n})

    def _disabled_items(self, top_n: list) -> list:
        return [
            {**item, "comments_status": "disabled"} if isinstance(item, dict) else item
            for item in top_n
        ]

    def _comments_config(self, state: PipelineState) -> dict:
        cfg = state.platform_config.get("comments", {})
        return cfg if isinstance(cfg, dict) else {}

    def _max_videos(self, state: PipelineState) -> int:
        return int(self._comments_config(state).get("max_videos", 5))

    def _max_comments(self, state: PipelineState) -> int:
        return int(self._comments_config(state).get("max_comments_per_video", 20))

    def _comment_order(self, state: PipelineState) -> str:
        return str(self._comments_config(state).get("order", "relevance"))

    def _fetch_items(self, dict_items: list[dict], state: PipelineState) -> list[dict]:
        return dict_items[: self._max_videos(state)]

    def _service_inputs(self, fetch_items: list[dict], state: PipelineState) -> list[dict]:
        max_comments = self._max_comments(state)
        order = self._comment_order(state)
        return [self._service_input(item, max_comments, order) for item in fetch_items]

    def _service_input(self, item: dict, max_comments: int, order: str) -> dict:
        return {**item, "_max_comments": max_comments, "_order": order}

    def _enriched_items(self, fetch_items: list[dict], results: list) -> list[dict]:
        enriched: list[dict] = []
        for fetch_item, result in zip(fetch_items, results, strict=True):
            enriched.append(self._enriched_item(fetch_item, result))
        return enriched

    def _enriched_item(self, fetch_item: dict, result: object) -> dict:
        merged = self._result_item(result)
        return merged if merged is not None else {**fetch_item, "comments_status": "failed"}

    def _result_item(self, result: object) -> dict | None:
        return first_tech_output(result, dict)

    def _not_attempted_items(self, dict_items: list[dict], state: PipelineState) -> list[dict]:
        return [
            {**item, "comments_status": "not_attempted"}
            for item in dict_items[self._max_videos(state) :]
        ]


class YouTubeSummaryStage(BaseStage):
    """Generate LLM summaries for top-N items."""

    def stage_name(self) -> str:
        return "summary"

    @log_with_time("[srp] youtube/summary: execute")
    async def execute(self, state: PipelineState) -> PipelineState:
        from social_research_probe.services.enriching.summary import SummaryService

        top_n = list(state.get_stage_output("comments").get("top_n", []))
        if not self._is_enabled(state) or not top_n:
            state.set_stage_output("summary", {"top_n": top_n})
            return state
        augmented = await self._items_with_surrogates(top_n)
        summary_results = await SummaryService().execute_batch(dict_items(augmented))
        enriched = self._items_with_summaries(augmented, summary_results)
        state.set_stage_output("summary", {"top_n": enriched})
        return state

    async def _items_with_surrogates(self, top_n: list) -> list:
        from social_research_probe.services.enriching.text_surrogate import TextSurrogateService

        results = await TextSurrogateService().execute_batch(dict_items(top_n))
        return self._merge_surrogates(top_n, results)

    def _merge_surrogates(self, top_n: list, results: list) -> list:
        result_by_index = iter(results)
        augmented = []
        for item in top_n:
            augmented.append(self._item_with_surrogate(item, result_by_index))
        return augmented

    def _item_with_surrogate(self, item: object, result_by_index: object) -> object:
        if not isinstance(item, dict):
            return item
        surrogate = self._surrogate_from_result(next(result_by_index))
        if not isinstance(surrogate, dict):
            return item
        return {
            **item,
            "text_surrogate": surrogate,
            "evidence_tier": surrogate.get("evidence_tier", "metadata_only"),
        }

    def _surrogate_from_result(self, result: object) -> object:
        return first_tech_output(result, dict, require_success=True, require_truthy=True)

    def _items_with_summaries(self, augmented: list, summary_results: list) -> list:
        result_by_index = iter(summary_results)
        enriched: list[dict] = []
        for item in augmented:
            enriched.append(self._item_with_summary(item, result_by_index))
        return enriched

    def _item_with_summary(self, item: object, result_by_index: object) -> object:
        if not isinstance(item, dict):
            return item
        merged = self._summary_from_result(next(result_by_index))
        return merged if isinstance(merged, dict) else dict(item)

    def _summary_from_result(self, result: object) -> object:
        return first_tech_output(result, dict)


class YouTubeCorroborateStage(BaseStage):
    """Corroborate claims in top-N items via configured search providers."""

    def stage_name(self) -> str:
        return "corroborate"

    @log_with_time("[srp] youtube/corroborate: execute")
    async def execute(self, state: PipelineState) -> PipelineState:
        from social_research_probe.services.corroborating.corroborate import CorroborationService

        top_n = list(state.get_stage_output("summary").get("top_n", []))
        if not self._is_enabled(state) or not top_n:
            state.set_stage_output("corroborate", {"top_n": top_n})
            return state
        service = CorroborationService()
        if not service.providers:
            state.set_stage_output("corroborate", {"top_n": top_n})
            return state
        corroboration_inputs = [item for item in top_n if isinstance(item, dict)]
        results = await service.execute_batch(corroboration_inputs)
        corroborated: list[dict] = []
        for result in results:
            item = next(
                (tr.output for tr in result.tech_results if isinstance(tr.output, dict)),
                None,
            )
            if item:
                corroborated.append(item)
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
        result = (await StatisticsService().execute_batch([{"scored_items": top_n}]))[0]
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

    @log_with_time("[srp] youtube/charts: execute")
    async def execute(self, state: PipelineState) -> PipelineState:
        from social_research_probe.services.analyzing.charts import ChartsService

        if not self._is_enabled(state):
            state.set_stage_output(
                "charts", {"chart_outputs": [], "chart_captions": [], "chart_takeaways": []}
            )
            return state
        items = self._scored_dataset(state)
        result = (await ChartsService().execute_batch([{"scored_items": items}]))[0]
        charts = next(
            (tr.output for tr in result.tech_results if tr.success and isinstance(tr.output, dict)),
            {"chart_outputs": [], "chart_captions": [], "chart_takeaways": []},
        )
        state.set_stage_output("charts", charts)
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
        from social_research_probe.services.synthesizing.synthesis import SynthesisService

        if not self._is_enabled(state):
            state.set_stage_output("synthesis", {"synthesis": ""})
            return state
        context = self._build_synthesis_context(state)
        result = (await SynthesisService().execute_batch([context]))[0]
        synthesis_text = next(
            (tr.output for tr in result.tech_results if tr.success and isinstance(tr.output, str)),
            "",
        )
        state.set_stage_output("synthesis", {"synthesis": synthesis_text})
        return state


class YouTubeAssembleStage(BaseStage):
    """Assemble all stage outputs into the final research report."""

    def stage_name(self) -> str:
        return "assemble"

    def _build_source_validation_summary(self, top_n: list) -> dict:
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

    @log_with_time("[srp] youtube/assemble: execute")
    async def execute(self, state: PipelineState) -> PipelineState:
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

        from social_research_probe.services.synthesizing.synthesis.runner import attach_synthesis

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
        from social_research_probe.services.reporting.report import ReportService

        if not self._is_enabled(state):
            return state

        report = state.outputs.get("report", {})
        allow_html = bool(state.platform_config.get("allow_html", True))
        result = (
            await ReportService().execute_batch([{"report": report, "allow_html": allow_html}])
        )[0]
        report_path = next(
            (tr.output for tr in result.tech_results if tr.success and isinstance(tr.output, str)),
            "",
        )
        report["report_path"] = report_path
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
            await AudioReportService().execute_batch([{"text": narration}])
        return state


class YouTubePipeline(BaseResearchPlatform):
    """Orchestrates all YouTube research stages and post-stage reports."""

    def stages(self) -> list[list[BaseStage]]:
        return [
            [YouTubeFetchStage()],
            [YouTubeClassifyStage()],
            [YouTubeScoreStage()],
            [YouTubeTranscriptStage(), YouTubeStatsStage(), YouTubeChartsStage()],
            [YouTubeCommentsStage()],
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
