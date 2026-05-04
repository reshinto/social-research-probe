"""Local watch scheduling helpers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

_INTERVALS = {
    "hourly": timedelta(hours=1),
    "daily": timedelta(days=1),
    "weekly": timedelta(days=7),
}


def due_status(watch: dict, now: datetime | None = None) -> tuple[bool, str]:
    """Return whether a watch is due and the reason."""
    interval = watch.get("interval")
    if not isinstance(interval, str) or not interval.strip():
        return False, "manual-only interval"
    duration = _INTERVALS.get(interval.strip().lower())
    if duration is None:
        return False, f"unsupported interval: {interval}"
    last_run_at = watch.get("last_run_at")
    if not isinstance(last_run_at, str) or not last_run_at.strip():
        return True, "never run"
    last = _parse_datetime(last_run_at)
    if last is None:
        return False, f"invalid last_run_at: {last_run_at}"
    current = now or datetime.now(UTC)
    if current - last >= duration:
        return True, f"due after {interval}"
    return False, f"not due until {(last + duration).isoformat()}"


def interval_seconds(interval: str) -> int:
    """Return local schedule interval seconds."""
    duration = _INTERVALS.get(interval)
    if duration is None:
        duration = _INTERVALS["daily"]
    return int(duration.total_seconds())


def cron_schedule(interval: str) -> str:
    """Return a simple cron schedule expression."""
    if interval == "hourly":
        return "0 * * * *"
    if interval == "weekly":
        return "0 9 * * 1"
    return "0 9 * * *"


def supported_intervals() -> tuple[str, ...]:
    """Return supported local schedule interval names."""
    return tuple(_INTERVALS)


def _parse_datetime(raw: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
