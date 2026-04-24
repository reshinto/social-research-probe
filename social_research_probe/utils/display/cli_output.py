"""CLI output formatting helpers."""

from __future__ import annotations

import json
import sys


def _emit(data: object, fmt: str) -> None:
    """Write *data* to stdout in the requested format."""
    if fmt == "json":
        json.dump(data, sys.stdout)
        sys.stdout.write("\n")
    elif fmt == "markdown":
        sys.stdout.write(_to_markdown(data) + "\n")
    else:
        sys.stdout.write(_to_text(data) + "\n")


def _to_text(data: object) -> str:
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
    return "```\n" + _to_text(data) + "\n```"
