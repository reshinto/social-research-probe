"""String utilities."""

import re

_MULTI_SPACE = re.compile(r" {2,}")


def normalize_whitespace(value: str) -> str:
    """Strip, lowercase, and collapse internal whitespace."""
    return _MULTI_SPACE.sub(" ", value.strip().lower())
