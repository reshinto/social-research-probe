"""YouTube research platform: concrete stage implementations and pipeline runner."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from social_research_probe.platform.base import BaseResearchPlatform, BaseStage
from social_research_probe.platform.state import PipelineState
from social_research_probe.services.analyzing.charts import ChartsService
from social_research_probe.services.analyzing.statistics import StatisticsService
from social_research_probe.services.enriching.summary import SummaryService
from social_research_probe.services.enriching.transcript import TranscriptService
from social_research_probe.services.reporting.audio import AudioReportService
from social_research_probe.services.reporting.html import HtmlReportService
from social_research_probe.services.scoring.score import ScoringService
from social_research_probe.services.synthesizing.synthesis import SynthesisService

if TYPE_CHECKING:
    from social_research_probe.services.base import ServiceResult


def _first_success(result: ServiceResult) -> object:
    """Return the first successful tech result output, or None."""
    for tr in result.tech_results:
        if tr.success and tr.output is not None:
            return tr.output
    return None


def _top_n_limit(state: PipelineState) -> int:
    platform_config = state.inputs.get("platform_config") or {}
    return int(platform_config.get("enrich_top_n", 5)) if isinstance(platform_config, dict) else 5


class YouTubeFetchStage(BaseStage):
    """Fetch and enrich YouTube search results via the platform adapter."""

    def stage_name(self) -> str:
        return "fetch"

    async def execute(self, state: PipelineState) -> PipelineState:
        empty: dict = {"items": [], "signals": []}
        if not self._is_enabled(state):
            state.set_stage_output("fetch", empty)
            return state
        adapter = state.inputs.get("adapter")
        limits = state.inputs.get("limits")
        search_topic = state.inputs.get("search_topic") or state.inputs.get("topic", "")
        if not adapter:
            state.set_stage_output("fetch", empty)
            return state
        raw = await asyncio.to_thread(adapter.search, search_topic, limits)
        items = await adapter.enrich(raw)
        signals = adapter.to_signals(items)
        state.set_stage_output("fetch", {"items": items, "signals": signals})
        return state


class YouTubeScoreStage(BaseStage):
    """Score and rank fetched items using trust/trend/opportunity signals."""

    def stage_name(self) -> str:
        return "score"

    async def execute(self, state: PipelineState) -> PipelineState:
        fetch = state.get_stage_output("fetch")
        items = fetch.get("items", [])
        limit = _top_n_limit(state)
        fallback: dict = {"all_scored": items, "top_n": items[:limit]}
        if not self._is_enabled(state) or not items:
            state.set_stage_output("score", fallback)
            return state
        weights = state.inputs.get("scoring_weights")
        svc = ScoringService()
        result = await svc.execute_one({"items": items, "weights": weights}, cfg=state.cfg)
        scored = _first_success(result) or items
        top_n = scored[:limit]
        state.set_stage_output("score", {"all_scored": scored, "top_n": top_n})
        return state


class YouTubeEnrichStage(BaseStage):
    """Enrich top-N items with transcripts and LLM summaries."""

    def stage_name(self) -> str:
        return "enrich"

    async def execute(self, state: PipelineState) -> PipelineState:
        top_n = list(state.get_stage_output("score").get("top_n", []))
        if not self._is_enabled(state) or not top_n:
            state.set_stage_output("enrich", {"top_n": top_n})
            return state

        transcript_svc = TranscriptService()
        summary_svc = SummaryService()

        transcript_results = await asyncio.gather(
            *(transcript_svc.execute_one(item, cfg=state.cfg) for item in top_n)
        )
        enriched: list[dict] = []
        for item, tr in zip(top_n, transcript_results):
            row = dict(item) if isinstance(item, dict) else {}
            transcript = _first_success(tr)
            if transcript:
                row["transcript"] = transcript
            enriched.append(row)

        summary_results = await asyncio.gather(
            *(summary_svc.execute_one(item, cfg=state.cfg) for item in enriched)
        )
        final: list[dict] = []
        for item, sr in zip(enriched, summary_results):
            summary = _first_success(sr)
            if summary:
                item["summary"] = summary
            final.append(item)

        state.set_stage_output("enrich", {"top_n": final})
        return state


class YouTubeCorroborateStage(BaseStage):
    """Corroborate claims in top-N items via configured search backends."""

    def stage_name(self) -> str:
        return "corroborate"

    async def execute(self, state: PipelineState) -> PipelineState:
        enrich = state.get_stage_output("enrich")
        score = state.get_stage_output("score")
        top_n = list(enrich.get("top_n") or score.get("top_n", []))
        backends = list(state.inputs.get("corroboration_backends") or [])
        if not self._is_enabled(state) or not top_n or not backends:
            state.set_stage_output("corroborate", {"top_n": top_n})
            return state

        from social_research_probe.corroboration.host import corroborate_claim
        from social_research_probe.technologies.validation.claim_extractor import Claim

        sem = asyncio.Semaphore(3)

        async def _run_one(item: dict) -> dict:
            title = item.get("title", "") if isinstance(item, dict) else str(item)
            url = item.get("url") if isinstance(item, dict) else None
            claim = Claim(text=title, source_text=title, index=0, source_url=url)
            async with sem:
                try:
                    corr = await corroborate_claim(claim, backends)
                    out = dict(item) if isinstance(item, dict) else {}
                    out["corroboration"] = corr
                    return out
                except Exception:
                    return dict(item) if isinstance(item, dict) else {}

        corroborated = list(await asyncio.gather(*(_run_one(item) for item in top_n)))
        state.set_stage_output("corroborate", {"top_n": corroborated})
        return state


class YouTubeAnalyzeStage(BaseStage):
    """Run statistics, charts, and synthesis on the corroborated results."""

    def stage_name(self) -> str:
        return "analyze"

    async def execute(self, state: PipelineState) -> PipelineState:
        corroborate = state.get_stage_output("corroborate")
        score = state.get_stage_output("score")
        top_n = list(corroborate.get("top_n") or score.get("top_n", []))
        empty: dict = {
            "top_n": top_n,
            "stats_summary": {},
            "chart_captions": [],
            "chart_takeaways": [],
            "source_validation_summary": {},
            "warnings": [],
            "synthesis": "",
        }
        if not self._is_enabled(state):
            state.set_stage_output("analyze", empty)
            return state

        fetch = state.get_stage_output("fetch")
        payload = {"scored_items": top_n}
        stats_svc = StatisticsService()
        charts_svc = ChartsService()
        synthesis_svc = SynthesisService()

        stats_result, charts_result = await asyncio.gather(
            stats_svc.execute_one(payload, cfg=state.cfg),
            charts_svc.execute_one(payload, cfg=state.cfg),
        )
        stats_output = _first_success(stats_result)
        charts_output = _first_success(charts_result)

        synthesis_context: dict = {
            "top_n": top_n,
            "stats_results": stats_output,
            "chart_results": charts_output,
            "items": fetch.get("items", []),
            "signals": fetch.get("signals", []),
            "topic": state.inputs.get("topic", ""),
        }
        synth_result = await synthesis_svc.execute_one(synthesis_context, cfg=state.cfg)
        synthesis_text = _first_success(synth_result) or ""

        state.set_stage_output("analyze", {
            "top_n": top_n,
            "stats_summary": stats_output if isinstance(stats_output, dict) else {},
            "chart_captions": [],
            "chart_takeaways": [],
            "source_validation_summary": {},
            "warnings": [],
            "synthesis": synthesis_text,
        })
        return state


def _assemble_packet(state: PipelineState) -> dict:
    """Build a ResearchPacket dict from accumulated stage outputs."""
    from social_research_probe.synthesize.evidence import summarize as summarize_evidence
    from social_research_probe.synthesize.evidence import summarize_signals
    from social_research_probe.synthesize.formatter import build_packet

    fetch = state.get_stage_output("fetch")
    corroborate = state.get_stage_output("corroborate")
    score = state.get_stage_output("score")
    analyze = state.get_stage_output("analyze")

    items = fetch.get("items", [])
    signals = fetch.get("signals", [])
    top_n = corroborate.get("top_n") or score.get("top_n", [])

    cmd = state.cmd
    topic = state.inputs.get("topic", "")
    platform = getattr(cmd, "platform", "youtube")
    purpose_names = state.inputs.get("purpose_names", [])

    warnings = list(analyze.get("warnings", []))
    threshold = float(
        getattr(getattr(state.cfg, "tunables", None) or {}, "get", lambda k, d: d)(
            "summary_divergence_threshold", 0.4
        )
    )
    for item in top_n:
        divergence = item.get("summary_divergence") if isinstance(item, dict) else None
        if divergence is not None and divergence > threshold:
            title = (item.get("title") or "untitled")[:80]
            warnings.append(f"summary/transcript divergence on {title!r}: {divergence:.2f}")

    return build_packet(
        topic=topic,
        platform=platform,
        purpose_set=list(purpose_names),
        items_top_n=top_n,
        source_validation_summary=analyze.get("source_validation_summary", {}),
        platform_signals_summary=summarize_signals(signals),
        evidence_summary=summarize_evidence(items, signals, top_n),
        stats_summary=analyze.get("stats_summary", {}),
        chart_captions=analyze.get("chart_captions", []),
        chart_takeaways=analyze.get("chart_takeaways", []),
        warnings=warnings,
    )


class YouTubePipeline(BaseResearchPlatform):
    """Orchestrates all YouTube research stages and post-stage reports."""

    def stages(self) -> list[BaseStage]:
        return [
            YouTubeFetchStage(),
            YouTubeScoreStage(),
            YouTubeEnrichStage(),
            YouTubeCorroborateStage(),
            YouTubeAnalyzeStage(),
        ]

    async def run(self, state: PipelineState) -> PipelineState:
        state = await self._run_stages(state)

        packet = _assemble_packet(state)

        html_svc = HtmlReportService()
        await html_svc.execute_one(
            {"packet": packet, "data_dir": state.data_dir},
            cfg=state.cfg,
        )

        audio_svc = AudioReportService()
        narration = str(packet.get("evidence_summary", ""))
        if narration:
            await audio_svc.execute_one({"text": narration}, cfg=state.cfg)

        state.outputs["packet"] = packet
        return state
