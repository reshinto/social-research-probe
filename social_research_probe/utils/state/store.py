"""Atomic JSON reader/writer. POSIX-atomic replace; fsync before rename."""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar, cast

from social_research_probe.utils.core.types import (
    JSONObject,
    PendingSuggestionsState,
    PurposesState,
    TopicsState,
)

StateDocument = TypeVar("StateDocument", TopicsState, PurposesState, PendingSuggestionsState)


def read_json(path: Path, default_factory: Callable[[], StateDocument]) -> StateDocument:
    """Read JSON from disk or user input.

    This utility is shared across commands, services, and stages, so the rule lives here instead of
    being reimplemented differently at each call site.

    Args:
        path: Filesystem location used to read, write, or resolve project data.
        default_factory: Default factory value that changes the behavior described by this
                         helper.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            read_json(
                path=Path("report.html"),
                default_factory="AI safety",
            )
        Output:
            "AI safety"
    """
    if not path.exists():
        data = default_factory()
        atomic_write_json(path, data)
        return data
    return cast(StateDocument, json.loads(path.read_text(encoding="utf-8")))


def atomic_write_json(path: Path, data: JSONObject) -> None:
    """Write JSON atomically: tmp -> fsync -> os.replace.

    This utility is shared across commands, services, and stages, so the rule lives here instead of
    being reimplemented differently at each call site.

    Args:
        path: Filesystem location used to read, write, or resolve project data.
        data: Input payload at this service, technology, or pipeline boundary.

    Returns:
        None. The result is communicated through state mutation, file/database writes, output, or an
        exception.

    Examples:
        Input:
            atomic_write_json(
                path=Path("report.html"),
                data={"title": "Example", "url": "https://youtu.be/demo"},
            )
        Output:
            None
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, path)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise
