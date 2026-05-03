"""File I/O helpers for reading and writing JSON files safely.

Why this exists: raw ``open``/``json.load`` calls scattered across the codebase
risk partial writes on crash and silently swallow missing-file errors.  This
module centralises JSON I/O behind two simple functions with predictable
semantics: reads return a safe default when the file is absent, and writes are
atomic (write-then-rename) so the target file is never seen in a half-written
state.

Called by: FilesystemCache (cache.py), state stores, and any command that
persists or reads structured data from disk.
"""

from __future__ import annotations

import contextlib
import dataclasses
import json
import os
from datetime import datetime
from pathlib import Path


def _srp_json_default(obj: object) -> object:
    """Convert project-specific objects into JSON-serializable values.

    This utility is shared across commands, services, and stages, so the rule lives here instead of
    being reimplemented differently at each call site.

    Args:
        obj: Python object being serialized for storage.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            _srp_json_default(
                obj={"title": "Example"},
            )
        Output:
            "AI safety"
    """
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return dataclasses.asdict(obj)  # is_dataclass() confirms this is safe
    if isinstance(obj, (Path, datetime)):
        return str(obj)
    return repr(obj)


def read_json(path: Path, default: object | None = None) -> object:
    """Read JSON from disk or user input.

    This utility is shared across commands, services, and stages, so the rule lives here instead of
    being reimplemented differently at each call site.

    Args:
        path: Filesystem location used to read, write, or resolve project data.
        default: Fallback value returned when the requested data is absent.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            read_json(
                path=Path("report.html"),
                default="AI safety",
            )
        Output:
            "AI safety"
    """
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        # Return a fresh copy so callers cannot mutate the default sentinel.
        return dict(default) if default is not None else {}


def write_json(path: Path, data: object) -> None:
    """Write *data* to a JSON file atomically, creating parent directories as needed.

    The function writes to a sibling ``.tmp`` file first, then renames it over the destination. On
    POSIX systems ``os.replace`` is atomic at the filesystem level, so readers will never observe a
    partial write.

    Non-standard types (dataclasses, Path, datetime, etc.) are handled by ``_srp_json_default`` so
    callers do not need to pre-convert values.

    Args:
        path: Filesystem location used to read, write, or resolve project data.
        data: Input payload at this service, technology, or pipeline boundary.

    Returns:
        None. The result is communicated through state mutation, file/database writes, output, or an
        exception.

    Raises:
                PermissionError: If the process lacks write permission for the parent
                    directory.

            Why this exists:
                A plain ``open(path, "w")`` write is *not* atomic — if the process
                crashes mid-write the file is left truncated or corrupt.  Writing to a
                ``.tmp`` sibling and renaming over the target is the standard POSIX
                idiom for atomic file replacement.


    Examples:
        Input:
            write_json(
                path=Path("report.html"),
                data={"title": "Example", "url": "https://youtu.be/demo"},
            )
        Output:
            None
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    tmp_path = path.with_suffix(".tmp")
    try:
        with open(tmp_path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, default=_srp_json_default)
        os.replace(tmp_path, path)
    except Exception:
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)
        raise
