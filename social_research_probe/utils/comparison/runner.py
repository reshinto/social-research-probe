"""Shared comparison runner used by CLI compare and local watches."""

from __future__ import annotations

import sqlite3


def build_run_info(row: dict, counts: dict) -> dict:
    """Build a RunInfo object from a research_runs row and count dict."""
    from social_research_probe.utils.comparison.types import RunInfo

    return RunInfo(
        run_pk=row["id"],
        run_id=row["run_id"],
        topic=row["topic"],
        platform=row["platform"],
        started_at=row.get("started_at") or "",
        finished_at=row.get("finished_at") or "",
        source_count=counts["sources"],
        claim_count=counts["claims"],
        narrative_count=counts["narratives"],
    )


def build_comparison(
    conn: sqlite3.Connection,
    baseline_row: dict,
    target_row: dict,
) -> dict:
    """Execute full deterministic comparison between two persisted runs."""
    from social_research_probe.technologies.persistence.sqlite.comparison_queries import (
        count_for_run,
        get_claims_for_run,
        get_narratives_for_run,
        get_sources_for_run,
    )
    from social_research_probe.utils.comparison.claims import compare_claims
    from social_research_probe.utils.comparison.narratives import compare_narratives
    from social_research_probe.utils.comparison.sources import compare_sources
    from social_research_probe.utils.comparison.summary import build_follow_ups
    from social_research_probe.utils.comparison.trends import derive_trends
    from social_research_probe.utils.comparison.types import ComparisonResult

    b_pk = baseline_row["id"]
    t_pk = target_row["id"]
    b_counts = count_for_run(conn, b_pk)
    t_counts = count_for_run(conn, t_pk)
    source_changes = compare_sources(
        get_sources_for_run(conn, b_pk), get_sources_for_run(conn, t_pk)
    )
    claim_changes = compare_claims(get_claims_for_run(conn, b_pk), get_claims_for_run(conn, t_pk))
    narrative_changes = compare_narratives(
        get_narratives_for_run(conn, b_pk), get_narratives_for_run(conn, t_pk)
    )
    result = ComparisonResult(
        baseline=build_run_info(baseline_row, b_counts),
        target=build_run_info(target_row, t_counts),
        source_changes=source_changes,
        claim_changes=claim_changes,
        narrative_changes=narrative_changes,
        trends=derive_trends(narrative_changes, claim_changes),
        counts={"baseline": b_counts, "target": t_counts},
        follow_ups=[],
    )
    result["follow_ups"] = build_follow_ups(result)
    return result
