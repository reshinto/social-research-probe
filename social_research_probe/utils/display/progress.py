"""Progress logging to stderr, gated by the debug technology-log switch.

The ``log`` function uses the same on/off gate as ``service_log`` (env
``SRP_LOGS`` or the config flag ``debug.technology_logs_enabled``). When the
gate is off the function is a silent no-op, so the CLI can reserve stdout for
the final report path.
"""

from __future__ import annotations

import sys
import time
from contextlib import contextmanager

from social_research_probe.utils.display.service_log import logs_enabled


def log(msg: str) -> None:
    """Print a [srp]-prefixed progress message to stderr when logs are enabled."""
    if not _enabled():
        return
    print(msg, file=sys.stderr)


@contextmanager
def timed_operation(msg: str):
    """Log operation start, run block, log result with elapsed time."""
    try:
        start = time.time()
        yield
        elapsed = time.time() - start
        log(f"{msg} outcome=success elapsed={elapsed:.2f}s")
    except Exception as exc:
        elapsed = time.time() - start
        log(f"{msg} outcome=error elapsed={elapsed:.2f}s err={exc}")
        raise


def _enabled() -> bool:
    """Return True iff technology logs are on; resilient to config-load errors."""
    try:
        from social_research_probe.config import load_active_config

        cfg = load_active_config()
        flag = bool(getattr(cfg, "debug", {}).get("technology_logs_enabled", False))
    except Exception:
        flag = False
    return logs_enabled(flag)
