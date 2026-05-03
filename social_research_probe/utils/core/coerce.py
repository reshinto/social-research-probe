"""Type-safe coercion helpers for untyped JSON values."""

from __future__ import annotations

import re

from social_research_probe.utils.core.types import JSONObject


def coerce_object(value: object) -> JSONObject:
    """Convert an untyped value into a safe object value.

    Normalizing here keeps loosely typed external values from spreading into business logic.

    Args:
        value: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
               to a provider.

    Returns:
        Dictionary with stable keys consumed by downstream project code.

    Examples:
        Input:
            coerce_object(
                value="42",
            )
        Output:
            {"enabled": True}
    """
    return value if isinstance(value, dict) else {}


def coerce_string(value: object) -> str:
    """Convert an untyped value into a safe string value.

    Normalizing here keeps loosely typed external values from spreading into business logic.

    Args:
        value: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
               to a provider.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            coerce_string(
                value="42",
            )
        Output:
            "AI safety"
    """
    return value if isinstance(value, str) else ""


def as_optional_string(value: object) -> str | None:
    """Return non-empty strings unchanged and represent every other value as None.

    This utility is shared across commands, services, and stages, so the rule lives here instead of
    being reimplemented differently at each call site.

    Args:
        value: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
               to a provider.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            as_optional_string(
                value="42",
            )
        Output:
            "AI safety"
    """
    return value if isinstance(value, str) and value else None


def coerce_int(value: object) -> int:
    """Convert an untyped value into a safe int value.

    Normalizing here keeps loosely typed external values from spreading into business logic.

    Args:
        value: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
               to a provider.

    Returns:
        Integer count, limit, status code, or timeout used by the caller.

    Examples:
        Input:
            coerce_int(
                value="42",
            )
        Output:
            5
    """
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return 0
    return 0


_DURATION_RE = re.compile(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?")


def parse_duration_seconds(duration: str) -> int:
    """Parse an ISO 8601 duration string (PTxHxMxS) into total seconds.

    This utility is shared across commands, services, and stages, so the rule lives here instead of
    being reimplemented differently at each call site.

    Args:
        duration: Elapsed duration value being coerced into a numeric field.

    Returns:
        Integer count, limit, status code, or timeout used by the caller.

    Examples:
        Input:
            parse_duration_seconds(
                duration="AI safety",
            )
        Output:
            5
    """
    m = _DURATION_RE.match(duration)
    if not m:
        return 0
    h, mn, s = (int(v or 0) for v in m.groups())
    return h * 3600 + mn * 60 + s
