"""
File I/O helpers for reading and writing JSON files safely.

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

import json
import os
from pathlib import Path


def read_json(path: Path, default: dict | None = None) -> dict:
    """Read a JSON file and return its contents as a dict.

    If the file does not exist the function returns a *copy* of ``default``
    (or an empty dict when ``default`` is ``None``) rather than raising
    ``FileNotFoundError``.  A copy is returned so that callers cannot
    accidentally mutate the default sentinel.

    Args:
        path: Absolute or relative path to the JSON file to read.
        default: Value to return when the file is absent.  Defaults to
            ``None``, which is treated as an empty dict ``{}``.

    Returns:
        The parsed JSON object (always a ``dict``), or a copy of ``default``
        (or ``{}``) when the file does not exist.

    Raises:
        json.JSONDecodeError: If the file exists but contains invalid JSON.
        PermissionError: If the process lacks read permission for the file.

    Why this exists:
        Returning a copy of ``default`` (rather than the object itself) prevents
        the classic "mutable default argument" footgun where two callers share
        the same dict object.
    """
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        # Return a fresh copy so callers cannot mutate the default sentinel.
        return dict(default) if default is not None else {}


def write_json(path: Path, data: dict) -> None:
    """Write *data* to a JSON file atomically, creating parent directories as needed.

    The function writes to a sibling ``.tmp`` file first, then renames it over
    the destination.  On POSIX systems ``os.replace`` is atomic at the
    filesystem level, so readers will never observe a partial write.

    Args:
        path: Destination path for the JSON file.  Parent directories are
            created automatically if they do not exist.
        data: The dict to serialise and write.  Must be JSON-serialisable.

    Returns:
        None

    Raises:
        TypeError: If ``data`` contains values that cannot be serialised to JSON.
        PermissionError: If the process lacks write permission for the parent
            directory.

    Why this exists:
        A plain ``open(path, "w")`` write is *not* atomic — if the process
        crashes mid-write the file is left truncated or corrupt.  Writing to a
        ``.tmp`` sibling and renaming over the target is the standard POSIX
        idiom for atomic file replacement.
    """
    path = Path(path)
    # Create parent directories so callers need not do it themselves.
    path.parent.mkdir(parents=True, exist_ok=True)

    # Place the temp file next to the target so the rename stays on the same
    # filesystem (cross-device renames are not atomic).
    tmp_path = path.with_suffix(".tmp")
    try:
        with open(tmp_path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        # os.replace is atomic on POSIX; on Windows it overwrites atomically too.
        os.replace(tmp_path, path)
    except Exception:
        # Best-effort cleanup of the temp file so we do not litter .tmp files.
        import contextlib

        with contextlib.suppress(OSError):
            os.unlink(tmp_path)
        raise
