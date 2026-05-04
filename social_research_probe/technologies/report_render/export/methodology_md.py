"""Methodology markdown builder: documents pipeline configuration and run coverage."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from pathlib import Path


def _bullet_list(values: list) -> str:
    """Return the bullet list.

    Report rendering has to turn loose research dictionaries into deterministic files, so each
    formatting rule is isolated and easy to review.

    Args:
        values: User-provided values to validate and normalize.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _bullet_list(
                values=["AI safety", "model evaluation"],
            )
        Output:
            "AI safety"
    """
    if not values:
        return "- None\n"
    return "".join(f"- {v}\n" for v in values)


def _section_research_query(report: dict) -> str:
    """Build the research query section for the methodology export.

    Keeping export text here prevents renderers from duplicating wording and column order.

    Args:
        report: Research report dictionary being rendered, exported, or persisted.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _section_research_query(
                report={"topic": "AI safety", "items_top_n": []},
            )
        Output:
            "AI safety"
    """
    topic = report.get("topic") or "N/A"
    return f"## Research Query\n\n{topic}\n\n"


def _section_platform_date(report: dict) -> str:
    """Build the platform date section for the methodology export.

    Keeping export text here prevents renderers from duplicating wording and column order.

    Args:
        report: Research report dictionary being rendered, exported, or persisted.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _section_platform_date(
                report={"topic": "AI safety", "items_top_n": []},
            )
        Output:
            "AI safety"
    """
    platform = report.get("platform") or "N/A"
    ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    return f"## Platform & Date\n\n- Platform: {platform}\n- Generated: {ts}\n\n"


def _section_purpose_set(report: dict) -> str:
    """Build the purpose set section for the methodology export.

    Keeping export text here prevents renderers from duplicating wording and column order.

    Args:
        report: Research report dictionary being rendered, exported, or persisted.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _section_purpose_set(
                report={"topic": "AI safety", "items_top_n": []},
            )
        Output:
            "AI safety"
    """
    purposes = report.get("purpose_set") or []
    return f"## Purpose Set\n\n{_bullet_list(purposes)}\n"


def _yt_config_lines(yt: dict) -> list[str]:
    """Build the yt config lines used in generated methodology output.

    Report rendering has to turn loose research dictionaries into deterministic files, so each
    formatting rule is isolated and easy to review.

    Args:
        yt: YouTube report subsection used by methodology export.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            _yt_config_lines(
                yt={"enabled": True},
            )
        Output:
            ["AI safety", "model evaluation"]
    """
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
    """Build the scoring weight lines used in generated methodology output.

    Report rendering has to turn loose research dictionaries into deterministic files, so each
    formatting rule is isolated and easy to review.

    Args:
        config: Configuration or context values that control this run.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            _scoring_weight_lines(
                config={"enabled": True},
            )
        Output:
            ["AI safety", "model evaluation"]
    """
    weights = config.get("scoring", {}).get("weights") or {}
    if not weights:
        return []
    return ["- scoring weights:"] + [f"  - {k}: {v}" for k, v in weights.items()]


def _section_pipeline_config(config: dict) -> str:
    """Build the pipeline config section for the methodology export.

    Keeping export text here prevents renderers from duplicating wording and column order.

    Args:
        config: Configuration or context values that control this run.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _section_pipeline_config(
                config={"enabled": True},
            )
        Output:
            "AI safety"
    """
    lines = _yt_config_lines(config) + _scoring_weight_lines(config)
    body = "\n".join(lines) if lines else "N/A"
    return f"## Pipeline Configuration\n\n{body}\n\n"


def _tech_status(enabled: object) -> str:
    """Document the tech status rule at the boundary where callers use it.

    Report rendering has to turn loose research dictionaries into deterministic files, so each
    formatting rule is isolated and easy to review.

    Args:
        enabled: Flag that selects the branch for this operation.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _tech_status(
                enabled=True,
            )
        Output:
            "AI safety"
    """
    return "enabled" if enabled else "disabled"


def _section_technologies(config: dict) -> str:
    """Return the section technologies.

    Report rendering has to turn loose research dictionaries into deterministic files, so each
    formatting rule is isolated and easy to review.

    Args:
        config: Configuration or context values that control this run.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _section_technologies(
                config={"enabled": True},
            )
        Output:
            "AI safety"
    """
    techs = config.get("technologies") or {}
    if not techs:
        return ""
    lines = [f"- {name}: {_tech_status(val)}" for name, val in techs.items()]
    return "## Technologies\n\n" + "\n".join(lines) + "\n\n"


def _tier_distribution(items: list[dict]) -> dict[str, int]:
    """Summarize tier distribution for report metadata.

    Report rendering has to turn loose research dictionaries into deterministic files, so each
    formatting rule is isolated and easy to review.

    Args:
        items: Ordered source items being carried through the current pipeline step.

    Returns:
        Dictionary with stable keys consumed by downstream project code.

    Examples:
        Input:
            _tier_distribution(
                items=[{"title": "Example", "url": "https://youtu.be/demo"}],
            )
        Output:
            {"enabled": True}
    """
    return dict(Counter(it.get("evidence_tier", "unknown") for it in items if isinstance(it, dict)))


def _status_counts(items: list[dict], field: str) -> dict[str, int]:
    """Summarize status counts for report metadata.

    Report rendering has to turn loose research dictionaries into deterministic files, so each
    formatting rule is isolated and easy to review.

    Args:
        items: Ordered source items being carried through the current pipeline step.
        field: Metric or data field read from source items.

    Returns:
        Dictionary with stable keys consumed by downstream project code.

    Examples:
        Input:
            _status_counts(
                items=[{"title": "Example", "url": "https://youtu.be/demo"}],
                field="AI safety",
            )
        Output:
            {"enabled": True}
    """
    return dict(Counter(it.get(field, "unknown") for it in items if isinstance(it, dict)))


def _section_evidence_coverage(report: dict) -> str:
    """Build the evidence coverage section for the methodology export.

    Keeping export text here prevents renderers from duplicating wording and column order.

    Args:
        report: Research report dictionary being rendered, exported, or persisted.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _section_evidence_coverage(
                report={"topic": "AI safety", "items_top_n": []},
            )
        Output:
            "AI safety"
    """
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
    """Document the timing table rule at the boundary where callers use it.

    Report rendering has to turn loose research dictionaries into deterministic files, so each
    formatting rule is isolated and easy to review.

    Args:
        timings: Stage timing records used in methodology output.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _timing_table(
                timings=["AI safety"],
            )
        Output:
            "AI safety"
    """
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


def _section_claims_extraction(config: dict) -> str:
    """Build the claims extraction section for the methodology export.

    Keeping export text here prevents renderers from duplicating wording and column order.

    Args:
        config: Configuration or context values that control this run.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _section_claims_extraction(
                config={"enabled": True},
            )
        Output:
            "AI safety"
    """
    claims_cfg = config.get("claims") or {}
    use_llm = claims_cfg.get("use_llm", False)
    max_per_source = claims_cfg.get("max_claims_per_source", 10)
    max_chars = claims_cfg.get("max_claim_chars", 500)
    method_line = (
        "- Extraction method: LLM-backed with deterministic fallback"
        if use_llm
        else "- Extraction method: deterministic (pattern-matching)"
    )
    llm_line = (
        "- LLM-backed extraction enabled: yes" if use_llm else "- LLM-backed extraction enabled: no"
    )
    lines = [
        method_line,
        "- Rule types: fact_claim, opinion, prediction, recommendation, experience, "
        "question, objection, pain_point, market_signal",
        llm_line,
        f"- Max claims per source: {max_per_source}",
        f"- Max claim length (chars): {max_chars}",
        "- Limitations: pattern-based rules; may miss nuanced or implicit claims; "
        "recommendations matched only when keyword appears at sentence start (imperative form)",
    ]
    return "## Claims Extraction\n\n" + "\n".join(lines) + "\n\n"


def _section_narrative_clustering(config: dict) -> str:
    """Build the narrative clustering section for the methodology export.

    Args:
        config: Configuration or context values that control this run.

    Returns:
        Methodology section documenting narrative clustering configuration.

    Examples:
        Input:
            _section_narrative_clustering(
                config={"narratives": {"min_cluster_size": 2}},
            )
        Output:
            "## Narrative Clustering"
    """
    narr_cfg = config.get("narratives") or {}
    min_size = narr_cfg.get("min_cluster_size", 2)
    max_size = narr_cfg.get("max_cluster_size", 12)
    llm_summarize = narr_cfg.get("llm_summarize", False)
    lines = [
        "- Algorithm: deterministic entity co-occurrence (Union-Find)",
        f"- Minimum cluster size: {min_size}",
        f"- Maximum cluster size: {max_size} (split by claim_type when exceeded)",
        f"- LLM summarization: {'enabled' if llm_summarize else 'disabled'}",
        "- Cluster types: theme, objection, pain_point, opportunity, risk, "
        "market_signal, question, prediction, mixed",
        "- Scoring: confidence (mean), opportunity_score, risk_score per cluster",
        "- Fully local: no embeddings, no network calls, no LLM dependencies by default",
        "- Limitations: entity-less claims grouped by claim_type only; "
        "capped at 500 claims per run",
    ]
    return "## Narrative Clustering\n\n" + "\n".join(lines) + "\n\n"


def _section_stage_timings(report: dict) -> str:
    """Build the stage timings section for the methodology export.

    Keeping export text here prevents renderers from duplicating wording and column order.

    Args:
        report: Research report dictionary being rendered, exported, or persisted.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _section_stage_timings(
                report={"topic": "AI safety", "items_top_n": []},
            )
        Output:
            "AI safety"
    """
    timings = report.get("stage_timings") or []
    table = _timing_table(timings)
    body = table if table else "No stage timing data available.\n"
    return f"## Stage Timings\n\n{body}\n"


def _section_warnings(report: dict) -> str:
    """Build the warnings section for the methodology export.

    Keeping export text here prevents renderers from duplicating wording and column order.

    Args:
        report: Research report dictionary being rendered, exported, or persisted.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _section_warnings(
                report={"topic": "AI safety", "items_top_n": []},
            )
        Output:
            "AI safety"
    """
    warnings = report.get("warnings") or []
    return f"## Warnings & Limitations\n\n{_bullet_list(warnings)}\n"


def build_methodology(report: dict, config: dict) -> str:
    """Build methodology markdown from report and config.

    Report rendering has to turn loose research dictionaries into deterministic files, so each
    formatting rule is isolated and easy to review.

    Args:
        report: Research report dictionary being rendered, exported, or persisted.
        config: Configuration or context values that control this run.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            build_methodology(
                report={"topic": "AI safety", "items_top_n": []},
                config={"enabled": True},
            )
        Output:
            "AI safety"
    """
    sections = [
        "# Methodology\n\n",
        _section_research_query(report),
        _section_platform_date(report),
        _section_purpose_set(report),
        _section_pipeline_config(config),
        _section_technologies(config),
        _section_evidence_coverage(report),
        _section_claims_extraction(config),
        _section_narrative_clustering(config),
        _section_stage_timings(report),
        _section_warnings(report),
    ]
    return "".join(sections)


def write_methodology(content: str, path: Path) -> Path:
    """Write methodology markdown to path. Returns path.

    Report rendering has to turn loose research dictionaries into deterministic files, so each
    formatting rule is isolated and easy to review.

    Args:
        content: Text content that should be written to the export file.
        path: Filesystem location used to read, write, or resolve project data.

    Returns:
        None. The result is communicated through state mutation, file/database writes, output, or an
        exception.

    Examples:
        Input:
            write_methodology(
                content="AI safety",
                path=Path("report.html"),
            )
        Output:
            None
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path
