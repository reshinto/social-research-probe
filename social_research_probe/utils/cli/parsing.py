"""CLI argument parsing utilities."""

from __future__ import annotations

from social_research_probe.utils.core.errors import ValidationError


def _id_selector(raw: str):
    """Parse a comma-separated id list or the literal ``all``."""
    if not raw:
        return []
    if raw == "all":
        return "all"
    try:
        return [int(x.strip()) for x in raw.split(",") if x.strip()]
    except ValueError as exc:
        raise ValidationError(f"invalid id selector: {raw!r}") from exc
