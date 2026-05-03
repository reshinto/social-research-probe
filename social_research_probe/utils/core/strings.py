"""String utilities."""

from __future__ import annotations

import re
from datetime import UTC, datetime

_MULTI_SPACE = re.compile(r" {2,}")
_URL_RE = re.compile(r"https?://\S+")


def normalize_whitespace(value: str) -> str:
    """Strip, lowercase, and collapse internal whitespace.

    This utility is shared across commands, services, and stages, so the rule lives here instead of
    being reimplemented differently at each call site.

    Args:
        value: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
               to a provider.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            normalize_whitespace(
                value="42",
            )
        Output:
            "AI safety"
    """
    return _MULTI_SPACE.sub(" ", value.strip().lower())


def account_age_days(created_iso: str | None) -> int | None:
    """Return the account age days.

    This shared utility keeps one parsing or normalization rule in a single place instead of letting
    call sites drift apart.

    Args:
        created_iso: Timestamp used for recency filtering, age calculations, or persisted audit
                     metadata.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            account_age_days(
                created_iso="2026-01-01T00:00:00Z",
            )
        Output:
            "AI safety"
    """
    if not created_iso:
        return None
    created = datetime.fromisoformat(created_iso.replace("Z", "+00:00"))
    return (datetime.now(UTC) - created).days


def citation_markers(description: str | None) -> list[str]:
    """Document the citation markers rule at the boundary where callers use it.

    This utility is shared across commands, services, and stages, so the rule lives here instead of
    being reimplemented differently at each call site.

    Args:
        description: Source text, prompt text, or raw value being parsed, normalized, classified, or
                     sent to a provider.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            citation_markers(
                description="This tool reduces latency by 30%.",
            )
        Output:
            ["AI safety", "model evaluation"]
    """
    if not description:
        return []
    return _URL_RE.findall(description)
