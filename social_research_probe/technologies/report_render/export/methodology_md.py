"""Methodology markdown builder: documents pipeline configuration and run coverage."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from pathlib import Path


def _bullet_list(values: list) -> str:
    if not values:
        return "- None\n"
    return "".join(f"- {v}\n" for v in values)


def _section_research_query(report: dict) -> str:
    topic = report.get("topic") or "N/A"
    return f"## Research Query\n\n{topic}\n\n"


def _section_platform_date(report: dict) -> str:
    platform = report.get("platform") or "N/A"
    ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    return f"## Platform & Date\n\n- Platform: {platform}\n- Generated: {ts}\n\n"


def _section_purpose_set(report: dict) -> str:
    purposes = report.get("purpose_set") or []
    return f"## Purpose Set\n\n{_bullet_list(purposes)}\n"


def _yt_config_lines(yt: dict) -> list[str]:
    lines = []
    for key in ("max_items", "enrich_top_n", "recency_days"):
        if key in yt:
            lines.append(f"- {key}: {yt[key]}")
    comments = yt.get("comments") or {}
    if comments:
        lines.append("- comments:")
        for k, v in comments.items():
            lines.append(f"  - {k}: {v}")
    return lines


def _scoring_weight_lines(config: dict) -> list[str]:
    weights = config.get("scoring", {}).get("weights") or {}
    if not weights:
        return []
    return ["- scoring weights:"] + [f"  - {k}: {v}" for k, v in weights.items()]


def _section_pipeline_config(config: dict) -> str:
    yt = config.get("platforms", {}).get("youtube") or {}
    lines = _yt_config_lines(yt) + _scoring_weight_lines(config)
    body = "\n".join(lines) if lines else "N/A"
    return f"## Pipeline Configuration\n\n{body}\n\n"


def _tech_status(enabled: object) -> str:
    return "enabled" if enabled else "disabled"


def _section_technologies(config: dict) -> str:
    techs = config.get("technologies") or {}
    if not techs:
        return "## Technologies\n\nN/A\n\n"
    lines = [f"- {name}: {_tech_status(val)}" for name, val in techs.items()]
    return "## Technologies\n\n" + "\n".join(lines) + "\n\n"


def _tier_distribution(items: list[dict]) -> dict[str, int]:
    return dict(Counter(it.get("evidence_tier", "unknown") for it in items if isinstance(it, dict)))


def _status_counts(items: list[dict], field: str) -> dict[str, int]:
    return dict(Counter(it.get(field, "unknown") for it in items if isinstance(it, dict)))


def _section_evidence_coverage(report: dict) -> str:
    items = report.get("items_top_n") or []
    total = len(items)
    tiers = _tier_distribution(items)
    transcript_counts = _status_counts(items, "transcript_status")
    comments_counts = _status_counts(items, "comments_status")

    tier_lines = "\n".join(f"  - {t}: {c}" for t, c in sorted(tiers.items()))
    ts_lines = "\n".join(f"  - {s}: {c}" for s, c in sorted(transcript_counts.items()))
    cs_lines = "\n".join(f"  - {s}: {c}" for s, c in sorted(comments_counts.items()))

    body = f"- total items: {total}\n"
    if tier_lines:
        body += f"- evidence tiers:\n{tier_lines}\n"
    if ts_lines:
        body += f"- transcript_status:\n{ts_lines}\n"
    if cs_lines:
        body += f"- comments_status:\n{cs_lines}\n"

    return f"## Evidence Coverage\n\n{body}\n"


def _timing_table(timings: list) -> str:
    header = "| Stage | Elapsed (s) | Status |\n|-------|-------------|--------|\n"
    rows = ""
    for t in timings:
        if not isinstance(t, dict):
            continue
        stage = t.get("stage", "")
        elapsed = t.get("elapsed_s", "")
        status = t.get("status", "")
        rows += f"| {stage} | {elapsed} | {status} |\n"
    return header + rows if rows else ""


def _section_stage_timings(report: dict) -> str:
    timings = report.get("stage_timings") or []
    table = _timing_table(timings)
    body = table if table else "No stage timing data available.\n"
    return f"## Stage Timings\n\n{body}\n"


def _section_warnings(report: dict) -> str:
    warnings = report.get("warnings") or []
    return f"## Warnings & Limitations\n\n{_bullet_list(warnings)}\n"


def build_methodology(report: dict, config: dict) -> str:
    """Build methodology markdown from report and config."""
    sections = [
        "# Methodology\n\n",
        _section_research_query(report),
        _section_platform_date(report),
        _section_purpose_set(report),
        _section_pipeline_config(config),
        _section_technologies(config),
        _section_evidence_coverage(report),
        _section_stage_timings(report),
        _section_warnings(report),
    ]
    return "".join(sections)


def write_methodology(content: str, path: Path) -> Path:
    """Write methodology markdown to path. Returns path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path
