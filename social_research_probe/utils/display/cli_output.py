"""CLI output formatting helpers."""

from __future__ import annotations

import json
import sys


def emit(data: object, fmt: str) -> None:
    """Write *data* to stdout in the requested format.

    This utility is shared across commands, services, and stages, so the rule lives here instead of
    being reimplemented differently at each call site.

    Args:
        data: Input payload at this service, technology, or pipeline boundary.
        fmt: Requested output format, such as json or text.

    Returns:
        None. The result is communicated through state mutation, file/database writes, output, or an
        exception.

    Examples:
        Input:
            emit(
                data={"title": "Example", "url": "https://youtu.be/demo"},
                fmt="AI safety",
            )
        Output:
            None
    """
    if fmt == "json":
        json.dump(data, sys.stdout)
        sys.stdout.write("\n")
    elif fmt == "markdown":
        sys.stdout.write(_to_markdown(data) + "\n")
    else:
        sys.stdout.write(_to_text(data) + "\n")


def _to_text(data: object) -> str:
    """Document the to text rule at the boundary where callers use it.

    This utility is shared across commands, services, and stages, so the rule lives here instead of
    being reimplemented differently at each call site.

    Args:
        data: Input payload at this service, technology, or pipeline boundary.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _to_text(
                data={"title": "Example", "url": "https://youtu.be/demo"},
            )
        Output:
            "AI safety"
    """
    if isinstance(data, dict) and "topics" in data:
        return "\n".join(data["topics"]) if data["topics"] else "(no topics)"
    if isinstance(data, dict) and "purposes" in data:
        if not data["purposes"]:
            return "(no purposes)"
        return "\n".join(f"{k}: {v['method']}" for k, v in data["purposes"].items())
    if isinstance(data, str):
        return data
    return json.dumps(data, indent=2)


def _to_markdown(data: object) -> str:
    """Document the to markdown rule at the boundary where callers use it.

    This utility is shared across commands, services, and stages, so the rule lives here instead of
    being reimplemented differently at each call site.

    Args:
        data: Input payload at this service, technology, or pipeline boundary.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _to_markdown(
                data={"title": "Example", "url": "https://youtu.be/demo"},
            )
        Output:
            "AI safety"
    """
    return "```\n" + _to_text(data) + "\n```"
