"""Config flag lookup utilities."""

from __future__ import annotations


def stage_flag(name: str, *, default: bool) -> bool:
    """Check whether a pipeline stage is enabled."""
    from social_research_probe.config import load_active_config
    try:
        return load_active_config().stage_enabled(name)
    except Exception:
        return default


def service_flag(name: str, *, default: bool) -> bool:
    """Check whether a service is enabled."""
    from social_research_probe.config import load_active_config
    try:
        return load_active_config().service_enabled(name)
    except Exception:
        return default
