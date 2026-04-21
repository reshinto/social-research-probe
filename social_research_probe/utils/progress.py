"""Progress logging to stderr, gated by the service-log master switch.

The `log` function is kept as the single legacy sink used throughout the
codebase. In this refactor it no longer prints unconditionally — it consults
the same on/off gate as ``@service_log`` (env ``SRP_LOGS`` or the config flag
``logging.service_logs_enabled``). When the gate is off the function is a
silent no-op, so the CLI can reserve stdout for the final report path.

Why gate here instead of ripping out every caller: one change silences the
entire existing log surface without touching ~15 files of call sites.
"""

from __future__ import annotations

import sys

from social_research_probe.utils.service_log import logs_enabled


def log(msg: str) -> None:
    """Print a [srp]-prefixed progress message to stderr when logs are enabled."""
    if not _enabled():
        return
    print(msg, file=sys.stderr)


def _enabled() -> bool:
    """Return True iff service logs are on; resilient to config-load errors."""
    try:
        from social_research_probe.config import load_active_config

        flag = bool(load_active_config().logging.get("service_logs_enabled", False))
    except Exception:
        flag = False
    return logs_enabled(flag)
