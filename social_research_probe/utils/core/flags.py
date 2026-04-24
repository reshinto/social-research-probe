"""Config flag lookup utilities."""

from __future__ import annotations


def stage_flag(cfg: object, name: str, *, default: bool) -> bool:
    """Check whether a pipeline stage is enabled."""
    fn = getattr(cfg, "stage_enabled", None)
    if fn is None:
        return default
    try:
        return bool(fn(name))
    except Exception:
        return default


def service_flag(cfg: object, name: str, *, default: bool) -> bool:
    """Check whether a service is enabled."""
    fn = getattr(cfg, "service_enabled", None)
    if fn is None:
        return default
    try:
        return bool(fn(name))
    except Exception:
        return default
