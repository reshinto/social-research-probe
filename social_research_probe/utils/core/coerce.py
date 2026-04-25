"""Type-safe coercion helpers for untyped JSON values."""

from __future__ import annotations

import re

from social_research_probe.utils.core.types import JSONObject


def coerce_object(value: object) -> JSONObject:
    return value if isinstance(value, dict) else {}


def coerce_string(value: object) -> str:
    return value if isinstance(value, str) else ""


def as_optional_string(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def coerce_int(value: object) -> int:
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
    """Parse an ISO 8601 duration string (PTxHxMxS) into total seconds."""
    m = _DURATION_RE.match(duration)
    if not m:
        return 0
    h, mn, s = (int(v or 0) for v in m.groups())
    return h * 3600 + mn * 60 + s
