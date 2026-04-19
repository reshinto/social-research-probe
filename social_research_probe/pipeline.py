from __future__ import annotations

import math
import os
import statistics
from datetime import UTC, datetime
from typing import Literal

from social_research_probe.commands.parse import ParsedRunResearch
from social_research_probe.errors import ValidationError
from social_research_probe.llm.host import emit_packet
from social_research_probe.platforms.base import FetchLimits, RawItem, SignalSet, TrustHints
from social_research_probe.platforms.registry import get_adapter
from social_research_probe.purposes import registry as purpose_registry
from social_research_probe.purposes.merge import merge_purposes
from social_research_probe.scoring.combine import overall_score
from social_research_probe.scoring.opportunity import opportunity_score
from social_research_probe.scoring.trend import trend_score
from social_research_probe.scoring.trust import trust_score
from social_research_probe.stats import multi_regression
from social_research_probe.stats.selector import select_and_run, select_and_run_correlation
from social_research_probe.synthesize.evidence import summarize as summarize_evidence
from social_research_probe.synthesize.evidence import summarize_signals
from social_research_probe.synthesize.explain import explain as explain_stat
from social_research_probe.synthesize.formatter import build_packet
from social_research_probe.synthesize.warnings import detect as detect_warnings
from social_research_probe.validation.source import classify as classify_source
from social_research_probe.viz import bar as bar_viz
from social_research_probe.viz import heatmap as heatmap_viz
from social_research_probe.viz import histogram as histogram_viz
from social_research_probe.viz import line as line_viz
from social_research_probe.viz import regression_scatter as regression_scatter_viz
from social_research_probe.viz import residuals as residuals_viz
from social_research_probe.viz import scatter as scatter_viz
from social_research_probe.viz import table as table_viz

Mode = Literal["skill", "cli"]

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
) -> tuple[float, dict]:
    src = classify_source(item, hints)
    trust = trust_score(
        source_class=_SRC_NUM[src.value],
        channel_credibility=_channel_credibility(hints.subscriber_count),
        citation_traceability=min(1.0, len(hints.citation_markers) / 3),
        ai_slop_penalty=0.0,
        corroboration_score=0.3,
    )
    age_days = max(
        1.0, (datetime.now(UTC) - signal.upload_date).days if signal.upload_date else 30.0
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
        "scores": {"trust": trust, "trend": trend, "opportunity": opportunity, "overall": overall},
        "features": {
            "view_velocity": signal.view_velocity or 0.0,
            "engagement_ratio": signal.engagement_ratio or 0.0,
            "age_days": age_days,
            "subscriber_count": float(hints.subscriber_count or 0),
        },
        "one_line_takeaway": (item.text_excerpt or item.title)[:140],
    }


def _build_stats_summary(scored_items: list[dict]) -> dict:
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
    results = select_and_run(overall, label="overall_score")
    results += select_and_run_correlation(
        trust, opportunity, label_a="trust", label_b="opportunity"
    )
    results += multi_regression.run(
        overall,
        {
            "trust": trust,
            "trend": [d["scores"]["trend"] for d in scored_items],
            "opportunity": opportunity,
        },
        label="overall",
    )
    models_run = _stats_models_for(len(overall))
    if len(overall) >= 2:
        models_run.append("correlation")
    if len(overall) >= 5:
        models_run.append("multi_regression")
    return {
        "models_run": models_run,
        "highlights": [explain_stat(r) for r in results],
        "low_confidence": len(overall) < 8,
    }


def _stats_models_for(n: int) -> list[str]:
    models: list[str] = []
    if n >= 1:
        models.append("descriptive")
    if n >= 2:
        models += ["spread", "regression"]
    if n >= 3:
        models += ["growth", "outliers"]
    return models


def _render_charts(scored_items: list[dict], data_dir) -> list[str]:
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


def _render_bar(overall: list[float], charts_dir) -> str:
    chart = bar_viz.render(overall, label="overall_score", output_dir=str(charts_dir))
    return chart.caption


def _render_line(overall: list[float], charts_dir) -> str:
    chart = line_viz.render(overall, label="overall_score_by_rank", output_dir=str(charts_dir))
    return f"{chart.caption}\n_(see PNG: {chart.path})_"


def _render_scatter(x: list[float], y: list[float], label: str, charts_dir) -> str:
    chart = scatter_viz.render(x, y, label=label, output_dir=str(charts_dir))
    return f"Scatter: {label.replace('_', ' ')} ({len(x)} items)\n_(see PNG: {chart.path})_"


def _render_histogram(values: list[float], charts_dir) -> str:
    chart = histogram_viz.render(values, label="overall_score", output_dir=str(charts_dir))
    return f"{chart.caption}\n_(see PNG: {chart.path})_"


def _render_regression(x: list[float], y: list[float], label: str, charts_dir) -> str:
    chart = regression_scatter_viz.render(x, y, label=label, output_dir=str(charts_dir))
    return f"{chart.caption}\n_(see PNG: {chart.path})_"


def _render_heatmap(scored_items: list[dict], charts_dir) -> str:
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


def _render_residuals(x: list[float], y: list[float], label: str, charts_dir) -> str:
    chart = residuals_viz.render(x, y, label=label, output_dir=str(charts_dir))
    return f"{chart.caption}\n_(see PNG: {chart.path})_"


def _render_table(top5: list[dict], charts_dir) -> str:
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


def run_research(
    cmd: ParsedRunResearch,
    data_dir,
    mode: Mode,
    adapter_config: dict | None = None,
) -> dict:
    _maybe_register_fake()
    purposes = purpose_registry.load(data_dir)["purposes"]
    config = {"data_dir": data_dir, **(adapter_config or {})}
    adapter = get_adapter(cmd.platform, config)
    if not adapter.health_check():
        raise ValidationError(f"adapter {cmd.platform} failed health check")

    packets: list[dict] = []
    for topic, purpose_names in cmd.topics:
        for n in purpose_names:
            if n not in purposes:
                raise ValidationError(f"unknown purpose: {n!r}")
        merged = merge_purposes(purposes, list(purpose_names))
        search_topic = _enrich_query(topic, merged.method)
        items = adapter.enrich(adapter.search(search_topic, FetchLimits()))
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
        svs = {
            "validated": 0,
            "partially": 0,
            "unverified": len(top5),
            "low_trust": sum(1 for d in top5 if d["scores"]["trust"] < 0.4),
            "primary": sum(1 for d in top5 if d["source_class"] == "primary"),
            "secondary": sum(1 for d in top5 if d["source_class"] == "secondary"),
            "commentary": sum(1 for d in top5 if d["source_class"] == "commentary"),
            "notes": "corroboration not run; use 'srp corroborate-claims' for validation",
        }
        stats_summary = _build_stats_summary(all_scored)
        chart_captions = _render_charts(all_scored, data_dir)
        warnings = detect_warnings(items, signals, top5)
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

    combined = (
        packets[0]
        if len(packets) == 1
        else {"multi": packets, "response_schema": packets[0]["response_schema"]}
    )
    if mode == "skill":
        emit_packet(combined, kind="synthesis")  # exits 0
    return combined
