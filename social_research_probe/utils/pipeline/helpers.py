"""Pure pipeline helper utilities."""

from __future__ import annotations


def collect_divergence_warnings(top_n: list, threshold: float) -> list[str]:
    """Return divergence warning strings for items exceeding threshold."""
    warnings: list[str] = []
    for item in top_n:
        divergence = item.get("summary_divergence") if isinstance(item, dict) else None
        if divergence is not None and divergence > threshold:
            title = (item.get("title") or "untitled")[:80]
            warnings.append(f"summary/transcript divergence on {title!r}: {divergence:.2f}")
    return warnings
