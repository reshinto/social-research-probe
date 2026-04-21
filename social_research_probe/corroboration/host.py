"""Orchestrates multiple corroboration backends for a single claim.

What: Provides corroborate_claim(), which fans out to each named backend,
collects CorroborationResults, and aggregates them into a single verdict.

Why: Keeps aggregation logic (majority vote, weighted confidence) separate
from backend HTTP/subprocess details so each piece is unit-testable in isolation.

Who calls it: pipeline steps and CLI commands that need to check a claim against
one or more external sources.
"""

from __future__ import annotations

import asyncio
import sys
from collections import Counter

from social_research_probe.corroboration.base import CorroborationResult
from social_research_probe.corroboration.registry import canonical_backend_name, get_backend
from social_research_probe.utils.pipeline_cache import (
    corroboration_cache,
    get_json,
    hash_key,
    set_json,
)


def aggregate_verdict(results: list[CorroborationResult]) -> tuple[str, float]:
    """Compute a combined verdict and confidence from a list of backend results.

    Algorithm:
    - Majority vote across the verdicts in ``results``.
    - Ties (no single verdict has a strict majority) resolve to 'inconclusive'.
    - Aggregate confidence is the weighted average of individual confidences,
      where each weight equals the backend's own confidence value.

    Args:
        results: Non-empty list of CorroborationResult objects from one or more
            backends. Empty list returns ('inconclusive', 0.0).

    Returns:
        A 2-tuple (verdict: str, confidence: float) where verdict is one of
        'supported', 'refuted', or 'inconclusive' and confidence is in [0.0, 1.0].
    """
    if not results:
        return ("inconclusive", 0.0)

    counts: Counter[str] = Counter(r.verdict for r in results)
    top_verdicts = counts.most_common()

    if len(top_verdicts) >= 2 and top_verdicts[0][1] == top_verdicts[1][1]:
        winner = "inconclusive"
    else:
        winner = top_verdicts[0][0]

    total_weight = sum(r.confidence for r in results)
    avg_confidence = (
        sum(r.confidence * r.confidence for r in results) / total_weight
        if total_weight > 0.0
        else 0.0
    )
    avg_confidence = max(0.0, min(1.0, avg_confidence))

    return (winner, avg_confidence)


async def corroborate_claim(claim, backend_names: list[str]) -> dict:
    """Run a claim through multiple backends concurrently and aggregate results.

    Each backend is fetched from the registry and awaited directly — backends
    expose async corroborate() so no thread wrapping is needed.

    Backends that raise any exception are skipped with a warning printed to
    stderr so the pipeline can continue with partial data.

    Results are cached on disk by ``(claim_text, sorted_backends)`` with a
    short TTL so repeat research runs within the hour skip external API calls.

    Args:
        claim: A Claim dataclass instance (from validation/claims.py).
        backend_names: Ordered list of backend name strings, e.g.
            ["exa", "brave", "llm_search"].

    Returns:
        Dict with claim_text, results, aggregate_verdict, aggregate_confidence.
    """
    import dataclasses

    normalized_backends = list(
        dict.fromkeys(canonical_backend_name(name) for name in backend_names)
    )
    cache = corroboration_cache()
    cache_key = hash_key("claim", claim.text, ",".join(sorted(normalized_backends)))
    cached = get_json(cache, cache_key)
    if cached is not None:
        return cached

    async def _call_backend(backend_name: str) -> CorroborationResult | None:
        try:
            backend = get_backend(backend_name)
            return await backend.corroborate(claim)
        except Exception as exc:
            print(f"[corroboration] backend {backend_name!r} failed: {exc}", file=sys.stderr)
            return None

    outcomes = await asyncio.gather(
        *[_call_backend(name) for name in normalized_backends],
        return_exceptions=False,
    )
    collected = [r for r in outcomes if r is not None]
    verdict, confidence = aggregate_verdict(collected)

    result = {
        "claim_text": claim.text,
        "results": [dataclasses.asdict(r) for r in collected],
        "aggregate_verdict": verdict,
        "aggregate_confidence": confidence,
    }
    set_json(cache, cache_key, result)
    return result
