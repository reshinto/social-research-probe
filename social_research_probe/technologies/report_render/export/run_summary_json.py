"""Run summary JSON builder: machine-readable metadata for a completed research run."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from social_research_probe.utils.io.io import write_json


def _item_counts(items: list[dict]) -> dict[str, int]:
    total = len(items)
    enriched = sum(
        1
        for it in items
        if isinstance(it, dict)
        and it.get("transcript_status") not in (None, "not_attempted", "disabled")
    )
    return {"fetched": total, "enriched": enriched}


def _evidence_tiers(items: list[dict]) -> dict[str, int]:
    return dict(Counter(it.get("evidence_tier", "unknown") for it in items if isinstance(it, dict)))


def _corroboration_summary(items: list[dict]) -> dict[str, int]:
    return dict(
        Counter(
            it.get("corroboration_verdict", "unknown")
            for it in items
            if isinstance(it, dict) and "corroboration_verdict" in it
        )
    )


def _config_snapshot(config: dict) -> dict:
    yt = config.get("platforms", {}).get("youtube") or {}
    weights = config.get("scoring", {}).get("weights") or {}
    snapshot: dict = {}
    if yt:
        snapshot["youtube"] = {k: v for k, v in yt.items() if not isinstance(v, dict)}
    if weights:
        snapshot["scoring_weights"] = dict(weights)
    return snapshot


def build_run_summary(report: dict, config: dict, artifact_paths: dict[str, str]) -> dict:
    """Build machine-readable run summary dict."""
    items = report.get("items_top_n") or []
    return {
        "topic": report.get("topic", ""),
        "platform": report.get("platform", ""),
        "timestamp": datetime.now(UTC).isoformat(),
        "purpose_set": list(report.get("purpose_set") or []),
        "item_count": _item_counts(items),
        "evidence_tiers": _evidence_tiers(items),
        "corroboration_summary": _corroboration_summary(items),
        "stage_timings": list(report.get("stage_timings") or []),
        "config_snapshot": _config_snapshot(config),
        "artifact_paths": dict(artifact_paths),
        "warnings": list(report.get("warnings") or []),
    }


def write_run_summary(summary: dict, path: Path) -> Path:
    """Write run summary JSON to path atomically. Returns path."""
    write_json(path, summary)
    return path
