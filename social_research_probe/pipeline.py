from __future__ import annotations

import asyncio
import math
import os
import statistics
from datetime import UTC, datetime
from pathlib import Path

from social_research_probe.commands.parse import ParsedRunResearch
from social_research_probe.config import Config
from social_research_probe.errors import ValidationError
from social_research_probe.llm.ensemble import multi_llm_prompt
from social_research_probe.platforms.base import (
    FetchLimits,
    RawItem,
    SignalSet,
    TrustHints,
)
from social_research_probe.platforms.registry import get_adapter
from social_research_probe.purposes import registry as purpose_registry
from social_research_probe.purposes.merge import merge_purposes
from social_research_probe.scoring.combine import overall_score
from social_research_probe.scoring.opportunity import opportunity_score
from social_research_probe.scoring.trend import trend_score
from social_research_probe.scoring.trust import trust_score
from social_research_probe.stats import (
    bayesian_linear,
    bootstrap,
    derived_targets,
    huber_regression,
    hypothesis_tests,
    kaplan_meier,
    kmeans,
    logistic_regression,
    multi_regression,
    naive_bayes,
    nonparametric,
    normality,
    pca,
    polynomial_regression,
)
from social_research_probe.stats.selector import (
    select_and_run,
    select_and_run_correlation,
)
from social_research_probe.synthesize.evidence import summarize as summarize_evidence
from social_research_probe.synthesize.evidence import summarize_signals
from social_research_probe.synthesize.explain import explain as explain_stat
from social_research_probe.synthesize.formatter import build_packet
from social_research_probe.synthesize.warnings import detect as detect_warnings
from social_research_probe.types import (
    AdapterConfig,
    MultiResearchPacket,
    ResearchPacket,
    ScoredItem,
    SourceValidationSummary,
    StatsSummary,
)
from social_research_probe.utils.concurrency import run_coro
from social_research_probe.utils.progress import log
from social_research_probe.validation.source import classify as classify_source
from social_research_probe.viz import bar as bar_viz
from social_research_probe.viz import heatmap as heatmap_viz
from social_research_probe.viz import histogram as histogram_viz
from social_research_probe.viz import line as line_viz
from social_research_probe.viz import regression_scatter as regression_scatter_viz
from social_research_probe.viz import residuals as residuals_viz
from social_research_probe.viz import scatter as scatter_viz
from social_research_probe.viz import table as table_viz

_SRC_NUM = {"primary": 1.0, "secondary": 0.7, "commentary": 0.4, "unknown": 0.3}

_STOPWORDS = frozenset(
    {
        "the",
        "a",
        "an",
        "of",
        "for",
        "to",
        "and",
        "or",
        "in",
        "on",
        "with",
        "get",
        "my",
        "by",
        "via",
        "from",
        "about",
        "how",
        "what",
        "which",
        "track",
        "latest",
        "across",
        "channels",
        "velocity",
        "saturation",
        "emergence",
    }
)


def _enrich_query(topic: str, method: str) -> str:
    words = [w for w in method.lower().split() if w not in _STOPWORDS and len(w) > 2][:3]
    extra = " ".join(dict.fromkeys(words))
    return f"{topic} {extra}".strip() if extra else topic


def _channel_credibility(subscriber_count: int | None) -> float:
    if not subscriber_count:
        return 0.3
    return min(1.0, 0.15 * math.log10(max(1, subscriber_count)))


def _zscore(values: list[float]) -> list[float]:
    if len(values) < 2:
        return [0.0] * len(values)
    mu = statistics.mean(values)
    sd = statistics.stdev(values) or 1.0
    return [(v - mu) / sd for v in values]


def _maybe_register_fake() -> None:
    if os.environ.get("SRP_TEST_USE_FAKE_YOUTUBE") == "1":
        import importlib

        importlib.import_module("tests.fixtures.fake_youtube")


def _score_item(
    item: RawItem,
    signal: SignalSet,
    hints: TrustHints,
    z_view_velocity: float,
    z_engagement: float,
) -> tuple[float, ScoredItem]:
    src = classify_source(item, hints)
    trust = trust_score(
        source_class=_SRC_NUM[src.value],
        channel_credibility=_channel_credibility(hints.subscriber_count),
        citation_traceability=min(1.0, len(hints.citation_markers) / 3),
        ai_slop_penalty=0.0,
        corroboration_score=0.3,
    )
    age_days = max(
        1.0,
        (datetime.now(UTC) - signal.upload_date).days if signal.upload_date else 30.0,
    )
    trend = trend_score(
        z_view_velocity=z_view_velocity,
        z_engagement_ratio=z_engagement,
        z_cross_channel_repetition=signal.cross_channel_repetition or 0.0,
        age_days=age_days,
    )
    engagement = signal.engagement_ratio or 0.0
    opportunity = opportunity_score(
        market_gap=max(0.0, 1.0 - (signal.cross_channel_repetition or 0.0)),
        monetization_proxy=min(1.0, engagement * 20),
        feasibility=0.5,
        novelty=max(0.0, 1.0 - age_days / 180.0),
    )
    overall = overall_score(trust=trust, trend=trend, opportunity=opportunity)
    return overall, {
        "title": item.title,
        "channel": item.author_name,
        "url": item.url,
        "source_class": src.value,
        "scores": {
            "trust": trust,
            "trend": trend,
            "opportunity": opportunity,
            "overall": overall,
        },
        "features": {
            "view_velocity": signal.view_velocity or 0.0,
            "engagement_ratio": signal.engagement_ratio or 0.0,
            "age_days": age_days,
            "subscriber_count": float(hints.subscriber_count or 0),
        },
        "one_line_takeaway": (item.text_excerpt or item.title)[:140],
    }


def _build_summary_prompt(title: str, channel: str, transcript: str) -> str:
    """Build the prompt sent to the LLM ensemble for a 100-word video summary."""
    return (
        "Write a detailed summary of this YouTube video (minimum 100 words). Cover:\n"
        "- The main topic and what the video is about\n"
        "- The key arguments, findings, demonstrations, or announcements\n"
        "- Who the target audience is and what they should take away\n"
        "- Specific claims, tools, people, companies, or data points mentioned\n\n"
        "Be specific and factual. Do not start with 'This video' or 'In this video'.\n\n"
        f"Title: {title}\nChannel: {channel}\n\n"
        f"Transcript:\n{transcript}"
    )


def _fallback_transcript_summary(transcript: str, word_limit: int = 220) -> str:
    """Return a readable transcript-derived fallback when the LLM summary fails."""
    words = transcript.split()
    if not words:
        return transcript
    excerpt = " ".join(words[:word_limit]).strip()
    if len(words) > word_limit:
        excerpt += " ..."
    return excerpt


def _build_description_summary_prompt(item: ScoredItem) -> str:
    """Build the prompt for a 100-word summary based on video description only."""
    title = item.get("title", "")
    channel = item.get("channel", "")
    published = item.get("published_at", "")
    description = item.get("text_excerpt", "")
    return (
        "Write a summary of this YouTube video (minimum 100 words) using only the"
        " information provided below — no transcript is available.\n"
        "Cover: the main topic, likely key arguments or demonstrations, who the target"
        " audience is, and any specific people, tools, or events referenced.\n"
        "Do not invent content not present below."
        " Do not start with 'This video' or 'In this video'.\n\n"
        f"Title: {title}\nChannel: {channel}\nPublished: {published}\n\n"
        f"Description:\n{description}"
    )


async def _enrich_one(
    item: ScoredItem,
    fetch_transcript,
    fetch_transcript_whisper,
    whisper_sem: asyncio.Semaphore,
) -> None:
    """Fetch transcript and LLM summary for a single video item.

    Runs transcript fetch and LLM summary concurrently across items via
    asyncio.gather. Whisper fallback acquires ``whisper_sem`` to cap
    concurrent audio-download + ML-transcription jobs. Modifies item in place.

    When no transcript is available, falls back to an LLM summary built
    from the video title and description, marked as description-based.
    """
    title = item.get("title", "untitled")[:80]
    log(f"[srp] transcript: fetching for {title!r}")

    # Caption fetch runs in a thread; whisper fallback acquires the semaphore
    # only if the caption fetch returns nothing.
    text = await asyncio.to_thread(fetch_transcript, item["url"])
    if not (text and text.strip()):
        async with whisper_sem:
            text = await asyncio.to_thread(fetch_transcript_whisper, item["url"])

    cleaned = " ".join(text.split())[:6000] if text else ""

    if cleaned:
        item["transcript"] = cleaned
        item["summary_source"] = "transcript"
        log(f"[srp] summary: transcript-based for {title[:60]!r}")
        prompt = _build_summary_prompt(
            title=item.get("title", ""),
            channel=item.get("channel", ""),
            transcript=cleaned,
        )
        task_label = f"summarising transcript for {title[:60]!r}"
    else:
        item["summary_source"] = "description"
        log(f"[srp] summary: description-based for {title[:60]!r} (transcript unavailable)")
        prompt = _build_description_summary_prompt(item)
        task_label = f"summarising description for {title[:60]!r}"

    summary = await asyncio.to_thread(multi_llm_prompt, prompt, task=task_label)
    if summary:
        item["one_line_takeaway"] = summary
    elif cleaned:
        item["one_line_takeaway"] = _fallback_transcript_summary(cleaned)


def _enrich_top5_with_transcripts(top5: list[ScoredItem]) -> None:
    """Fetch transcripts and AI summaries for top-5 items concurrently.

    Transcript sources tried in order per item:
    1. YouTube captions via yt-dlp (``fetch_transcript``).
    2. Whisper transcription of the downloaded audio (``fetch_transcript_whisper``).

    All 5 items are processed in parallel via asyncio.gather so transcript
    downloads and LLM calls overlap. Whisper is capped at 2 concurrent jobs
    to prevent memory exhaustion. Item failures do not abort the batch.

    The full transcript (up to 6000 chars) is stored as item["transcript"].
    A 100-word+ summary from the multi-LLM ensemble is stored as
    item["one_line_takeaway"]. Falls back silently on any error.
    Modifies the dicts in place.
    """
    from social_research_probe.platforms.youtube.extract import fetch_transcript
    from social_research_probe.platforms.youtube.whisper_transcript import (
        fetch_transcript_whisper,
    )

    async def _gather() -> None:
        # Limit concurrent whisper jobs to 2 to avoid memory exhaustion from
        # simultaneous audio-download + ML-transcription across all top-5 items.
        whisper_sem = asyncio.Semaphore(2)
        await asyncio.gather(
            *[
                _enrich_one(item, fetch_transcript, fetch_transcript_whisper, whisper_sem)
                for item in top5
            ],
            return_exceptions=True,
        )

    run_coro(_gather())


def _fetch_best_transcript(url: str, primary_fn, fallback_fn) -> str | None:
    """Try primary transcript fetch; fall back to whisper if it returns nothing.

    Both callables accept a URL and return ``str | None``.
    All exceptions are swallowed so failures never crash the pipeline.
    """
    try:
        text = primary_fn(url)
    except Exception:
        text = None
    if text and text.strip():
        return text
    try:
        return fallback_fn(url)
    except Exception:
        return None


def _build_stats_summary(scored_items: list[ScoredItem]) -> StatsSummary:
    """Run all applicable stats analyses across the full scored dataset.

    Statistical confidence kicks in around n>=8 for moderate correlations,
    so the pipeline now passes every fetched item rather than only the
    top-5 — that lifts ``low_confidence`` to False once a real run lands.
    """
    if not scored_items:
        return {"models_run": [], "highlights": [], "low_confidence": True}
    overall = [d["scores"]["overall"] for d in scored_items]
    trust = [d["scores"]["trust"] for d in scored_items]
    opportunity = [d["scores"]["opportunity"] for d in scored_items]
    trend = [d["scores"]["trend"] for d in scored_items]
    ranks = [float(i) for i in range(len(overall))]
    results = select_and_run(overall, label="overall_score")
    results += select_and_run_correlation(
        trust, opportunity, label_a="trust", label_b="opportunity"
    )
    results += multi_regression.run(
        overall,
        {"trust": trust, "trend": trend, "opportunity": opportunity},
        label="overall",
    )
    results += normality.run(overall, label="overall_score")
    results += polynomial_regression.run(ranks, overall, label="overall", degree=2)
    results += polynomial_regression.run(ranks, overall, label="overall", degree=3)
    results += nonparametric.run_spearman(trust, opportunity, "trust", "opportunity")
    results += nonparametric.run_mann_whitney(
        overall[: len(overall) // 2],
        overall[len(overall) // 2 :],
        "top_half",
        "bottom_half",
    )
    results += hypothesis_tests.run_welch_t(
        overall[: len(overall) // 2],
        overall[len(overall) // 2 :],
        "top_half",
        "bottom_half",
    )
    results += bootstrap.run(overall, label="overall_score")
    results += _run_advanced_models(scored_items)
    models_run = _stats_models_for(len(overall))
    if len(overall) >= 2:
        models_run += ["correlation", "spearman", "mann_whitney", "welch_t"]
    if len(overall) >= 4:
        models_run += ["normality", "polynomial_deg2", "polynomial_deg3", "bootstrap"]
    if len(overall) >= 5:
        models_run += [
            "multi_regression",
            "logistic_regression",
            "kmeans",
            "pca",
            "kaplan_meier",
            "naive_bayes",
            "huber_regression",
            "bayesian_linear",
        ]
    return {
        "models_run": models_run,
        "highlights": [explain_stat(r) for r in results],
        "low_confidence": len(overall) < 8,
    }


def _run_advanced_models(scored_items: list[ScoredItem]) -> list:
    """Run batch-2 advanced models (logistic, k-means, PCA, survival, NB, Huber, Bayes).

    Each model short-circuits to an empty list when the dataset is too
    small for identifiability; the pipeline keeps running even when
    individual models decline to fit.
    """
    if len(scored_items) < 5:
        return []
    targets = derived_targets.build_targets(scored_items)
    feature_names = [
        "trust",
        "trend",
        "opportunity",
        "view_velocity",
        "engagement_ratio",
        "age_days",
        "subscribers",
    ]
    feature_cols = {name: targets[name] for name in feature_names}
    feature_matrix = [
        [targets[name][i] for name in feature_names] for i in range(len(scored_items))
    ]
    results: list = []
    results += logistic_regression.run(targets["is_top_5"], feature_cols, label="is_top_5")
    results += kmeans.run(feature_matrix, k=3, label="items")
    results += pca.run(feature_matrix, feature_names, n_components=2, label="features")
    results += kaplan_meier.run(
        targets["time_to_event_days"],
        targets["event_crossed_100k"],
        label="views>=100k",
    )
    results += naive_bayes.run(targets["is_top_5"], feature_cols, label="is_top_5")
    results += huber_regression.run(targets["rank"], targets["overall"], label="overall")
    results += bayesian_linear.run(
        targets["overall"],
        {
            "trust": targets["trust"],
            "trend": targets["trend"],
            "opportunity": targets["opportunity"],
        },
        label="overall",
    )
    return results


def _stats_models_for(n: int) -> list[str]:
    models: list[str] = []
    if n >= 1:
        models.append("descriptive")
    if n >= 2:
        models += ["spread", "regression"]
    if n >= 3:
        models += ["growth", "outliers"]
    return models


def _render_charts(scored_items: list[ScoredItem], data_dir: Path) -> list[str]:
    """Render the full advanced-stats chart suite from the scored dataset.

    Produces: bar, line (rank decay), regression-scatter with fitted line
    (trust vs opp and trust vs trend), plain scatters for backward compat,
    histogram of overall scores, correlation heatmap of all numeric
    features, residuals plot for the rank regression, plus a formatted
    top-10 table.
    """
    if not scored_items:
        return []
    charts_dir = data_dir / "charts"
    charts_dir.mkdir(parents=True, exist_ok=True)
    overall = [d["scores"]["overall"] for d in scored_items]
    trust = [d["scores"]["trust"] for d in scored_items]
    trend = [d["scores"]["trend"] for d in scored_items]
    opportunity = [d["scores"]["opportunity"] for d in scored_items]
    ranks = [float(i) for i in range(len(overall))]

    captions: list[str] = []
    captions.append(_render_bar(overall, charts_dir))
    captions.append(_render_line(overall, charts_dir))
    captions.append(_render_histogram(overall, charts_dir))
    captions.append(_render_regression(trust, opportunity, "trust_vs_opportunity", charts_dir))
    captions.append(_render_regression(trust, trend, "trust_vs_trend", charts_dir))
    captions.append(_render_scatter(trust, opportunity, "trust_vs_opportunity", charts_dir))
    captions.append(_render_scatter(trust, trend, "trust_vs_trend", charts_dir))
    captions.append(_render_heatmap(scored_items, charts_dir))
    captions.append(_render_residuals(ranks, overall, "overall_by_rank", charts_dir))
    captions.append(_render_table(scored_items[:10], charts_dir))
    return captions


def _render_bar(overall: list[float], charts_dir: Path) -> str:
    chart = bar_viz.render(overall, label="overall_score", output_dir=str(charts_dir))
    return chart.caption


def _render_line(overall: list[float], charts_dir: Path) -> str:
    chart = line_viz.render(overall, label="overall_score_by_rank", output_dir=str(charts_dir))
    return f"{chart.caption}\n_(see PNG: {chart.path})_"


def _render_scatter(x: list[float], y: list[float], label: str, charts_dir: Path) -> str:
    chart = scatter_viz.render(x, y, label=label, output_dir=str(charts_dir))
    return f"Scatter: {label.replace('_', ' ')} ({len(x)} items)\n_(see PNG: {chart.path})_"


def _render_histogram(values: list[float], charts_dir: Path) -> str:
    chart = histogram_viz.render(values, label="overall_score", output_dir=str(charts_dir))
    return f"{chart.caption}\n_(see PNG: {chart.path})_"


def _render_regression(x: list[float], y: list[float], label: str, charts_dir: Path) -> str:
    chart = regression_scatter_viz.render(x, y, label=label, output_dir=str(charts_dir))
    return f"{chart.caption}\n_(see PNG: {chart.path})_"


def _render_heatmap(scored_items: list[ScoredItem], charts_dir: Path) -> str:
    features = {
        "trust": [d["scores"]["trust"] for d in scored_items],
        "trend": [d["scores"]["trend"] for d in scored_items],
        "opportunity": [d["scores"]["opportunity"] for d in scored_items],
        "overall": [d["scores"]["overall"] for d in scored_items],
        "velocity": [d["features"]["view_velocity"] for d in scored_items],
        "engagement": [d["features"]["engagement_ratio"] for d in scored_items],
        "age_days": [d["features"]["age_days"] for d in scored_items],
    }
    chart = heatmap_viz.render(features, label="feature_correlations", output_dir=str(charts_dir))
    return f"{chart.caption}\n_(see PNG: {chart.path})_"


def _render_residuals(x: list[float], y: list[float], label: str, charts_dir: Path) -> str:
    chart = residuals_viz.render(x, y, label=label, output_dir=str(charts_dir))
    return f"{chart.caption}\n_(see PNG: {chart.path})_"


def _render_table(top5: list[ScoredItem], charts_dir: Path) -> str:
    rows = [
        {
            "rank": i + 1,
            "channel": d["channel"][:25],
            "trust": f"{d['scores']['trust']:.2f}",
            "trend": f"{d['scores']['trend']:.2f}",
            "opp": f"{d['scores']['opportunity']:.2f}",
            "overall": f"{d['scores']['overall']:.2f}",
        }
        for i, d in enumerate(top5)
    ]
    chart = table_viz.render(rows, label="top5_summary", output_dir=str(charts_dir))
    return f"{chart.caption}\n_(see PNG: {chart.path})_"


def _available_backends(data_dir: Path) -> list[str]:
    """Return corroboration backends allowed by config and available at runtime.

    ``backend = host`` auto-discovers the web-search backends whose credentials
    are configured. ``backend = llm_cli`` or a specific search backend uses only
    that backend. ``backend = none`` disables corroboration entirely.
    """
    from social_research_probe.corroboration.registry import get_backend
    from social_research_probe.errors import ValidationError

    configured = Config.load(data_dir).corroboration_backend
    if configured == "none":
        log(
            "[srp] corroboration: disabled in config (corroboration.backend = 'none'). Enable with 'srp config set corroboration.backend host'."
        )
        return []
    candidates = ("exa", "brave", "tavily") if configured == "host" else (configured,)

    available: list[str] = []
    for name in candidates:
        try:
            if get_backend(name).health_check():
                available.append(name)
        except ValidationError:
            pass

    if not available:
        checked = ", ".join(candidates)
        log(
            f"[srp] corroboration: backend '{configured}' configured but no provider usable"
            f" (checked: {checked}). Hint: run 'srp config check-secrets --corroboration {configured}'."
        )
    return available


async def _corroborate_one(
    item: ScoredItem,
    backends: list[str],
    sem: asyncio.Semaphore,
) -> dict:
    """Corroborate a single item using its title as the claim text.

    Runs inside an asyncio event loop created per worker thread so nested
    ``asyncio.run`` calls in ``corroborate_claim`` work safely.
    """
    from social_research_probe.corroboration.host import corroborate_claim
    from social_research_probe.validation.claims import Claim

    claim = Claim(
        text=item.get("title", ""),
        source_text=item.get("one_line_takeaway") or item.get("title", ""),
        index=0,
    )
    async with sem:
        return await asyncio.to_thread(corroborate_claim, claim, backends)


def _corroborate_top5(top5: list[ScoredItem], backends: list[str]) -> list[dict]:
    """Corroborate all top-5 items concurrently, one claim per item.

    Uses the video title as the claim text — short, factual, and searchable.
    The AI-generated one_line_takeaway is passed as source context. Caps
    concurrent API calls to 3 to respect search-backend rate limits.
    """
    log(f"[srp] corroboration: starting — {len(top5)} items to check via {', '.join(backends)}")

    async def _gather() -> list[dict]:
        sem = asyncio.Semaphore(3)
        results = await asyncio.gather(
            *[_corroborate_one(item, backends, sem) for item in top5],
            return_exceptions=True,
        )
        return [r if isinstance(r, dict) else {} for r in results]

    results = run_coro(_gather())
    verdicts = [r.get("aggregate_verdict", "no_result") for r in results]
    summary = ", ".join(
        f"{v}={verdicts.count(v)}"
        for v in ("supported", "inconclusive", "refuted", "no_result")
        if verdicts.count(v)
    )
    log(f"[srp] corroboration: done — {summary}")
    return results


def _build_svs(
    top5: list[ScoredItem],
    corroboration_results: list[dict],
    backends: list[str],
) -> SourceValidationSummary:
    """Build SourceValidationSummary from corroboration results (or defaults).

    Verdict mapping:
    - supported  → validated
    - inconclusive / refuted → partially (has a signal, outcome uncertain)
    - no results (empty dict or no backends ran) → unverified
    """
    if corroboration_results and backends:
        validated = sum(
            1 for r in corroboration_results if r.get("aggregate_verdict") == "supported"
        )
        partially = sum(
            1
            for r in corroboration_results
            if r.get("aggregate_verdict") in ("inconclusive", "refuted")
        )
        unverified = len(top5) - validated - partially
        notes = f"auto-corroborated via {', '.join(backends)}"
    else:
        validated = 0
        partially = 0
        unverified = len(top5)
        notes = "corroboration not run; use 'srp corroborate-claims' for validation"
    return {
        "validated": validated,
        "partially": partially,
        "unverified": max(0, unverified),
        "low_trust": sum(1 for d in top5 if d["scores"]["trust"] < 0.4),
        "primary": sum(1 for d in top5 if d["source_class"] == "primary"),
        "secondary": sum(1 for d in top5 if d["source_class"] == "secondary"),
        "commentary": sum(1 for d in top5 if d["source_class"] == "commentary"),
        "notes": notes,
    }


def run_research(
    cmd: ParsedRunResearch,
    data_dir: Path,
    adapter_config: AdapterConfig | None = None,
) -> ResearchPacket | MultiResearchPacket:
    _maybe_register_fake()
    os.environ["SRP_DATA_DIR"] = str(data_dir)
    purposes = purpose_registry.load(data_dir)["purposes"]
    cfg = Config.load(data_dir)
    platform_config: AdapterConfig = {
        **cfg.platform_defaults(cmd.platform),
        "data_dir": data_dir,
        **(adapter_config or {}),
    }
    limits = FetchLimits(
        max_items=int(platform_config.get("max_items", FetchLimits.max_items)),
        recency_days=platform_config.get("recency_days", FetchLimits.recency_days),
    )
    adapter = get_adapter(cmd.platform, platform_config)
    if not adapter.health_check():
        raise ValidationError(f"adapter {cmd.platform} failed health check")

    packets: list[ResearchPacket] = []
    for topic, purpose_names in cmd.topics:
        for n in purpose_names:
            if n not in purposes:
                raise ValidationError(f"unknown purpose: {n!r}")
        merged = merge_purposes(purposes, list(purpose_names))
        search_topic = _enrich_query(topic, merged.method)
        items = adapter.enrich(adapter.search(search_topic, limits))
        signals = adapter.to_signals(items)
        hints = [adapter.trust_hints(it) for it in items]
        z_vels = _zscore([s.view_velocity or 0.0 for s in signals])
        z_engs = _zscore([s.engagement_ratio or 0.0 for s in signals])
        scored = [
            _score_item(item, signal, hint, z_vel, z_eng)
            for item, signal, hint, z_vel, z_eng in zip(
                items, signals, hints, z_vels, z_engs, strict=True
            )
        ]
        scored.sort(key=lambda x: x[0], reverse=True)
        all_scored = [d for _, d in scored]
        top5 = all_scored[:5]
        if platform_config.get("fetch_transcripts", True) and cmd.platform == "youtube":
            _enrich_top5_with_transcripts(top5)
        backends = _available_backends(data_dir)
        corroboration_results = _corroborate_top5(top5, backends) if backends else []
        svs = _build_svs(top5, corroboration_results, backends)
        stats_summary = _build_stats_summary(all_scored)
        chart_captions = _render_charts(all_scored, data_dir)
        cfg_corr = Config.load(data_dir).corroboration_backend
        skip_reason: str | None = None
        if not backends:
            skip_reason = (
                "disabled in config"
                if cfg_corr == "none"
                else "no API credentials usable — run 'srp config check-secrets'"
            )
        warnings = detect_warnings(
            items,
            signals,
            top5,
            corroboration_ran=bool(backends and top5),
            corroboration_skip_reason=skip_reason,
        )
        packets.append(
            build_packet(
                topic=topic,
                platform=cmd.platform,
                purpose_set=list(merged.names),
                items_top5=top5,
                source_validation_summary=svs,
                platform_signals_summary=summarize_signals(signals),
                evidence_summary=summarize_evidence(items, signals, top5),
                stats_summary=stats_summary,
                chart_captions=chart_captions,
                warnings=warnings,
            )
        )

    combined = packets[0] if len(packets) == 1 else {"multi": packets}
    return combined
