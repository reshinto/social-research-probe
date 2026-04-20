"""Build SourceValidationSummary from corroboration results."""

from __future__ import annotations

from social_research_probe.types import ScoredItem, SourceValidationSummary


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
