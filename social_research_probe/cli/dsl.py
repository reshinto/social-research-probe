"""Lightweight DSL helpers for CLI argument parsing.

Supports quoted-pipe lists like ``"a"|"b"`` and quoted name=method pairs
like ``"name"="method"``. Falls back to positional values when no DSL
syntax is detected.
"""

from __future__ import annotations

from social_research_probe.utils.core.errors import ValidationError


def _take_quoted(src: str, pos: int) -> tuple[str, int]:
    if pos >= len(src) or src[pos] != '"':
        raise ValidationError(f"expected '\"' at position {pos} in {src!r}")
    end = src.find('"', pos + 1)
    if end == -1:
        raise ValidationError(f"unterminated quoted string in {src!r}")
    return src[pos + 1 : end], end + 1


def parse_quoted_list(src: str) -> list[str]:
    """Parse ``"a"|"b"|"c"`` into ``["a", "b", "c"]``."""
    values: list[str] = []
    pos = 0
    while pos < len(src):
        val, pos = _take_quoted(src, pos)
        values.append(val)
        if pos < len(src):
            if src[pos] != "|":
                raise ValidationError(f"expected '|' at position {pos} in {src!r}")
            pos += 1
    return values


def parse_topic_values(values: list[str]) -> list[str]:
    """Expand DSL forms in topic values; pass through positional ones."""
    if len(values) == 1 and values[0].startswith('"'):
        return parse_quoted_list(values[0])
    return values


def parse_name_method(values: list[str]) -> tuple[str, str]:
    """Parse a purpose ``--add`` value into ``(name, method)``.

    Accepts either positional ``[NAME, METHOD]`` or DSL ``"name"="method"``.
    """
    if len(values) == 1 and values[0].startswith('"'):
        src = values[0]
        name, pos = _take_quoted(src, 0)
        if src[pos : pos + 2] != '="':
            raise ValidationError(f"expected '=\"...\"' after name in {src!r}")
        method, end = _take_quoted(src, pos + 1)
        if end != len(src):
            raise ValidationError(f"unexpected trailing content in {src!r}")
        return name, method
    if len(values) == 2:
        return values[0], values[1]
    raise ValidationError('--add requires NAME METHOD or "name"="method"')
