"""CLI argument parsing utilities."""

from __future__ import annotations

from social_research_probe.utils.core.errors import ValidationError


def _id_selector(raw: str):
    """Return the ID selector.

    Command helpers keep user-facing parsing, validation, and output formatting out of pipeline and
    service code.

    Args:
        raw: Source text, prompt text, or raw value being parsed, normalized, classified, or sent to
             a provider.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            _id_selector(
                raw="42",
            )
        Output:
            "AI safety"
    """
    if not raw:
        return []
    if raw == "all":
        return "all"
    try:
        return [int(x.strip()) for x in raw.split(",") if x.strip()]
    except ValueError as exc:
        raise ValidationError(f"invalid id selector: {raw!r}") from exc
