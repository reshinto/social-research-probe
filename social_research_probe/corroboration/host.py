"""Orchestrates multiple corroboration backends for a single claim.

What: Provides corroborate_claim(), which fans out to each named backend,
collects CorroborationResults, and aggregates them into a single verdict.

Why: Keeps aggregation logic (majority vote, weighted confidence) separate
from backend HTTP/subprocess details so each piece is unit-testable in isolation.

Who calls it: pipeline steps and CLI commands that need to check a claim against
one or more external sources.
"""

from __future__ import annotations

import sys
from collections import Counter

from social_research_probe.corroboration.base import CorroborationResult
from social_research_probe.corroboration.registry import get_backend
from social_research_probe.errors import AdapterError


def aggregate_verdict(results: list[CorroborationResult]) -> tuple[str, float]:
    """Compute a combined verdict and confidence from a list of backend results.

    Algorithm:
    - Majority vote across the verdicts in ``results``.
    - Ties (no single verdict has a strict majority) resolve to 'inconclusive'.
    - Aggregate confidence is the weighted average of individual confidences,
      where each weight equals the backend's own confidence value. This rewards
      high-confidence backends and discounts uncertain ones.

    Args:
        results: Non-empty list of CorroborationResult objects from one or more
            backends. Empty list returns ('inconclusive', 0.0).

    Returns:
        A 2-tuple (verdict: str, confidence: float) where verdict is one of
        'supported', 'refuted', or 'inconclusive' and confidence is in [0.0, 1.0].
    """
    if not results:
        return ("inconclusive", 0.0)

    # Count votes for each verdict label.
    counts: Counter[str] = Counter(r.verdict for r in results)
    top_verdicts = counts.most_common()

    # Detect a tie: if the top two counts are equal, fall back to inconclusive.
    if len(top_verdicts) >= 2 and top_verdicts[0][1] == top_verdicts[1][1]:
        winner = "inconclusive"
    else:
        winner = top_verdicts[0][0]

    # Weighted-average confidence: each result's confidence weights itself.
    total_weight = sum(r.confidence for r in results)
    if total_weight == 0.0:
        # All backends returned 0 confidence — fall back to plain average.
        avg_confidence = sum(r.confidence for r in results) / len(results)
    else:
        avg_confidence = sum(r.confidence * r.confidence for r in results) / total_weight

    # Clamp to [0.0, 1.0] to guard against floating-point drift.
    avg_confidence = max(0.0, min(1.0, avg_confidence))

    return (winner, avg_confidence)


def corroborate_claim(claim, backend_names: list[str]) -> dict:
    """Run a claim through multiple backends and aggregate results.

    Each backend is fetched from the registry, called, and its result appended
    to a list. Backends that raise AdapterError are skipped with a warning
    printed to stderr so the pipeline can continue with partial data.

    Args:
        claim: A Claim dataclass instance (from validation/claims.py).
            The field claim.text is passed to each backend.
        backend_names: Ordered list of backend name strings to try, e.g.
            ["exa", "brave", "llm_cli"]. Names must be registered in the
            corroboration registry.

    Returns:
        Dict with four keys:
          - claim_text (str): the original claim text.
          - results (list[dict]): each CorroborationResult serialised to a
            plain dict via dataclasses.asdict().
          - aggregate_verdict (str): majority-vote verdict across all
            successful backends.
          - aggregate_confidence (float): weighted-average confidence score.

    Why: Returning a plain dict (not a dataclass) makes the output directly
    JSON-serialisable, which simplifies pipeline storage and CLI display.
    """
    import dataclasses

    collected: list[CorroborationResult] = []

    for backend_name in backend_names:
        try:
            backend = get_backend(backend_name)
            result = backend.corroborate(claim)
            collected.append(result)
        except AdapterError as exc:
            # Log the failure and continue with remaining backends.
            print(f"[corroboration] backend {backend_name!r} failed: {exc}", file=sys.stderr)

    verdict, confidence = aggregate_verdict(collected)

    return {
        "claim_text": claim.text,
        "results": [dataclasses.asdict(r) for r in collected],
        "aggregate_verdict": verdict,
        "aggregate_confidence": confidence,
    }
