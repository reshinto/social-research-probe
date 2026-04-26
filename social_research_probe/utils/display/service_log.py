"""Minimal service lifecycle logging + timing.

Each service call emits exactly two events (start, end) when logs are enabled.
Timings are always recorded into ``report["stage_timings"]`` so a Markdown
footer can render them later. Logs go to stderr; the CLI reserves stdout for
the final report path.
"""

from __future__ import annotations

import os
import sys
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, contextmanager
from typing import Literal, TypedDict

_TRUTHY = {"1", "true", "yes", "on"}


class StageTiming(TypedDict):
    """One entry in ``report["stage_timings"]``."""

    stage: str
    elapsed_s: float
    status: Literal["ok", "error"]
    error: str


def logs_enabled(cfg_flag: bool = False) -> bool:
    """Return True iff service logs should be emitted.

    Env var ``SRP_LOGS`` (``1|true|yes|on``) overrides the config flag; either
    one turning it on is sufficient. Off by default.
    """
    env = os.environ.get("SRP_LOGS", "").strip().lower()
    return env in _TRUTHY or bool(cfg_flag)


def _emit(line: str) -> None:
    """Write a single log line to stderr."""
    print(line, file=sys.stderr, flush=True)


@asynccontextmanager
async def service_log(
    name: str,
    *,
    report: dict,
    cfg_logs_enabled: bool = False,
) -> AsyncIterator[None]:
    """Bracket an async service call with start/end events + timing capture.

    Always appends one ``StageTiming`` entry to ``report["stage_timings"]``.
    Emits ``start`` / ``end`` lines to stderr only when ``logs_enabled``.
    On exception: records ``status="error"`` with the exception string, emits
    a failure line, then re-raises so callers can decide how to handle it.
    """
    enabled = logs_enabled(cfg_logs_enabled)
    timings = report.setdefault("stage_timings", [])
    if enabled:
        _emit(f"▶ {name} started")
    start = time.perf_counter()
    try:
        yield
    except Exception as exc:
        elapsed = time.perf_counter() - start
        timings.append(
            StageTiming(
                stage=name,
                elapsed_s=elapsed,
                status="error",
                error=str(exc),
            )
        )
        if enabled:
            _emit(f"✗ {name} failed in {elapsed:.2f}s: {exc}")
        raise
    else:
        elapsed = time.perf_counter() - start
        timings.append(StageTiming(stage=name, elapsed_s=elapsed, status="ok", error=""))
        if enabled:
            _emit(f"✓ {name} done in {elapsed:.2f}s")


@contextmanager
def service_log_sync(
    name: str,
    *,
    report: dict,
    cfg_logs_enabled: bool = False,
):
    """Bracket a sync service call with start/end events + timing capture."""
    enabled = logs_enabled(cfg_logs_enabled)
    timings = report.setdefault("stage_timings", [])
    if enabled:
        _emit(f"▶ {name} started")
    start = time.perf_counter()
    try:
        yield
    except Exception as exc:
        elapsed = time.perf_counter() - start
        timings.append(
            StageTiming(
                stage=name,
                elapsed_s=elapsed,
                status="error",
                error=str(exc),
            )
        )
        if enabled:
            _emit(f"✗ {name} failed in {elapsed:.2f}s: {exc}")
        raise
    else:
        elapsed = time.perf_counter() - start
        timings.append(StageTiming(stage=name, elapsed_s=elapsed, status="ok", error=""))
        if enabled:
            _emit(f"✓ {name} done in {elapsed:.2f}s")
