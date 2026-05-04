"""Config flag lookup utilities."""

from __future__ import annotations


def stage_flag(name: str, *, platform: str, default: bool) -> bool:
    """Check whether a pipeline stage is enabled.

    This shared utility keeps one parsing or normalization rule in a single place instead of letting
    call sites drift apart.

    Args:
        name: Registry, config, or CLI name used to select the matching project value.
        platform: Platform name, such as youtube or all, used to select config and pipeline
                  behavior.
        default: Flag that selects the branch for this operation.

    Returns:
        True when the condition is satisfied; otherwise False.

    Examples:
        Input:
            stage_flag(
                name="AI safety",
                platform="AI safety",
                default=True,
            )
        Output:
            True
    """
    from social_research_probe.config import load_active_config

    try:
        return load_active_config().stage_enabled(platform, name)
    except Exception:
        return default


def service_flag(name: str, *, default: bool) -> bool:
    """Check whether a service is enabled.

    This shared utility keeps one parsing or normalization rule in a single place instead of letting
    call sites drift apart.

    Args:
        name: Registry, config, or CLI name used to select the matching project value.
        default: Flag that selects the branch for this operation.

    Returns:
        True when the condition is satisfied; otherwise False.

    Examples:
        Input:
            service_flag(
                name="comments",
                default=True,
            )
        Output:
            True
    """
    from social_research_probe.config import load_active_config

    try:
        return load_active_config().service_enabled(name)
    except Exception:
        return default
