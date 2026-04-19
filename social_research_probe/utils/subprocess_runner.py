"""
Thin wrapper around ``subprocess.run`` with structured error handling.

Why this exists: raw ``subprocess.run`` calls scatter error-handling boilerplate
(returncode checks, timeout handling, stderr extraction) across every call site.
This module centralises that logic behind a single ``run`` function that raises
``AdapterError`` on failure, making it trivial for callers to propagate
command-line tool errors through the standard SRP exception hierarchy.

Called by: platform adapters and CLI commands that shell out to external tools
(e.g. yt-dlp, ffmpeg, git).
"""

from __future__ import annotations

import subprocess

from social_research_probe.errors import AdapterError


def run(
    argv: list[str],
    *,
    timeout: int = 30,
    input: str | None = None,
) -> subprocess.CompletedProcess:
    """Run a subprocess and return the completed process on success.

    The command is executed with ``capture_output=True`` and ``text=True`` so
    that stdout and stderr are available as strings on the returned
    ``CompletedProcess`` object.

    Args:
        argv: Command and arguments as a list of strings, e.g.
            ``["git", "status", "--short"]``.
        timeout: Maximum wall-clock seconds to wait for the subprocess to
            finish.  Defaults to 30.  The timeout is forwarded to
            ``subprocess.run`` unchanged.
        input: Optional string to write to the subprocess's stdin.  Pass
            ``None`` (the default) to leave stdin empty.

    Returns:
        A ``subprocess.CompletedProcess`` instance with ``returncode``,
        ``stdout``, and ``stderr`` attributes populated.

    Raises:
        AdapterError: If the process exits with a non-zero return code, or if
            the timeout expires before the process finishes.
        Any other exception raised by ``subprocess.run`` (e.g.
            ``FileNotFoundError`` when the executable is not found) is *not*
            caught and propagates to the caller unchanged.

    Why this exists:
        Raising ``AdapterError`` (rather than letting ``CalledProcessError`` or
        ``TimeoutExpired`` bubble up) keeps the rest of the codebase insulated
        from subprocess internals and aligns with SRP's structured exception
        hierarchy (§9 of the spec).
    """
    try:
        result = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=timeout,
            input=input,
        )
    except subprocess.TimeoutExpired as exc:
        raise AdapterError(f"command {argv[0]!r} timed out after {timeout}s") from exc

    if result.returncode != 0:
        raise AdapterError(
            f"command {argv[0]!r} failed (exit {result.returncode}): {result.stderr.strip()}"
        )

    return result
