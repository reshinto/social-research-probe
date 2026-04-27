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
    """Read JSON; if file missing, seed with default_factory() and persist."""
    if not path.exists():
        data = default_factory()
        atomic_write_json(path, data)
        return data
    return cast(StateDocument, json.loads(path.read_text(encoding="utf-8")))


def atomic_write_json(path: Path, data: JSONObject) -> None:
    """Write JSON atomically: tmp -> fsync -> os.replace."""
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
