"""Research pipeline package — orchestrates adapter, scoring, stats, and synthesis."""

from __future__ import annotations

from social_research_probe.config import Config

from .charts import _render_charts
from .corroboration import _corroborate_top5
from .enrichment import (
    _build_description_summary_prompt,
    _build_summary_prompt,
    _enrich_top5_with_transcripts,
    _fallback_transcript_summary,
    _fetch_best_transcript,
)
from .orchestrator import _available_backends, _maybe_register_fake, get_adapter, run_research
from .scoring import _channel_credibility, _enrich_query, _score_item, _zscore
from .stats import _build_stats_summary, _run_advanced_models, _stats_models_for
from .svs import _build_svs

__all__ = [
    "Config",
    "_available_backends",
    "_build_description_summary_prompt",
    "_build_stats_summary",
    "_build_summary_prompt",
    "_build_svs",
    "_channel_credibility",
    "_corroborate_top5",
    "_enrich_query",
    "_enrich_top5_with_transcripts",
    "_fallback_transcript_summary",
    "_fetch_best_transcript",
    "_maybe_register_fake",
    "_render_charts",
    "_run_advanced_models",
    "_score_item",
    "_stats_models_for",
    "_zscore",
    "get_adapter",
    "run_research",
]
