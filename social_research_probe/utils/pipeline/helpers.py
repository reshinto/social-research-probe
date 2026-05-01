"""Pure pipeline helper utilities."""

from __future__ import annotations


def _has_real_transcript(item: dict) -> bool:
    status = item.get("transcript_status")
    if status is not None and status != "available":
        return False
    transcript = item.get("transcript")
    return isinstance(transcript, str) and bool(transcript.strip())


def collect_divergence_warnings(top_n: list, threshold: float) -> list[str]:
    """Return divergence warning strings for items exceeding threshold."""
    warnings: list[str] = []
    for item in top_n:
        if not isinstance(item, dict):
            continue
        if not _has_real_transcript(item):
            continue
        divergence = item.get("summary_divergence")
        if divergence is not None and divergence > threshold:
            title = (item.get("title") or "untitled")[:80]
            warnings.append(f"summary/transcript divergence on {title!r}: {divergence:.2f}")
    return warnings
