"""Deterministic per-sample metrics for the reliability harness.

Pure-function package: no LLM calls, no network. Used by both the Phase 9
narrow summary-quality script and the Phase 10 generalized harness.
"""

from __future__ import annotations

import re
import statistics

_PROPER_NOUN_RE = re.compile(r"\b[A-Z][A-Za-z0-9]{2,}\b")


def coverage(summary: str, required_tokens: list[str]) -> float:
    """Fraction of ``required_tokens`` present in ``summary`` (case-insensitive)."""
    if not required_tokens:
        return 1.0
    text = summary.lower()
    hits = sum(1 for t in required_tokens if t.lower() in text)
    return hits / len(required_tokens)


def hallucinated_names(summary: str, source_text: str, allowed: list[str]) -> list[str]:
    """Return sorted proper nouns present in summary but not in source/allowed.

    Case-insensitive comparison. ``source_text`` is typically the transcript
    the summary was derived from.
    """
    allowed_lower = {a.lower() for a in allowed}
    source_lower = source_text.lower()
    candidates = set(_PROPER_NOUN_RE.findall(summary))
    return sorted(
        {w for w in candidates if w.lower() not in allowed_lower and w.lower() not in source_lower}
    )


def length_compliance(summary: str, target_words: int, tolerance: int = 5) -> bool:
    """True when ``summary`` word count is in ``[target - tolerance, target]``."""
    wc = len(summary.split())
    return (target_words - tolerance) <= wc <= target_words


def aggregate(values: list[float]) -> dict[str, float]:
    """Return mean / stdev / min / max / p5 / p95 over ``values``.

    Empty input returns zeros across the board rather than raising.
    """
    if not values:
        return {"mean": 0.0, "stdev": 0.0, "min": 0.0, "max": 0.0, "p5": 0.0, "p95": 0.0}
    if len(values) == 1:
        v = values[0]
        return {"mean": v, "stdev": 0.0, "min": v, "max": v, "p5": v, "p95": v}
    ordered = sorted(values)
    n = len(ordered)
    return {
        "mean": statistics.mean(values),
        "stdev": statistics.stdev(values),
        "min": ordered[0],
        "max": ordered[-1],
        "p5": ordered[max(0, round(0.05 * (n - 1)))],
        "p95": ordered[min(n - 1, round(0.95 * (n - 1)))],
    }
