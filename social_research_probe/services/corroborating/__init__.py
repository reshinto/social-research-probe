"""Corroboration services: registry, provider helpers, and claim orchestration."""

from __future__ import annotations

from social_research_probe.technologies.corroborates import (
    CorroborationProvider,
    CorroborationResult,
    aggregate_verdict,
    corroborate_claim,
    ensure_providers_registered,
    get_provider,
    list_providers,
    register,
)


def auto_mode_providers() -> tuple[str, ...]:
    """Return ordered provider names to try in auto mode.

    Services translate platform data into adapter calls and normalize the result so stages can
    handle success, skip, and failure consistently.

    Returns:
        Tuple whose positions are part of the public helper contract shown in the example.

    Examples:
        Input:
            auto_mode_providers()
        Output:
            ("AI safety", "Find unmet needs")
    """
    from social_research_probe.config import load_active_config

    cfg = load_active_config()
    if not cfg.service_enabled("corroboration"):
        return ()
    return ("exa", "brave", "tavily", "llm_search")


def _candidates(configured: str) -> tuple[str, ...]:
    """Document the candidates rule at the boundary where callers use it.

    Services translate platform data into adapter calls and normalize the result so stages can
    handle success, skip, and failure consistently.

    Args:
        configured: Configured provider mode, including explicit names or auto selection.

    Returns:
        Tuple whose positions are part of the public helper contract shown in the example.

    Examples:
        Input:
            _candidates(
                configured="AI safety",
            )
        Output:
            ("AI safety", "Find unmet needs")
    """
    return auto_mode_providers() if configured == "auto" else (configured,)


def _llm_search_allowed(name: str) -> bool:
    """Report whether the LLM search provider is allowed to run.

    Services translate platform data into adapter calls and normalize the result so stages can
    handle success, skip, and failure consistently.

    Args:
        name: Registry, config, or CLI name used to select the matching project value.

    Returns:
        True when the condition is satisfied; otherwise False.

    Examples:
        Input:
            _llm_search_allowed(
                name="codex",
            )
        Output:
            True
    """
    from social_research_probe.config import load_active_config

    if name != "llm_search":
        return True
    return load_active_config().service_enabled("llm")


def select_healthy_providers(configured: str) -> tuple[list[str], tuple[str, ...]]:
    """Resolve configured corroboration provider to healthy provider names.

    Returns (healthy, candidates). Service-level gates are applied here so callers (pipeline
    stages) need not check service feature flags directly.

    Args:
        configured: Configured provider mode, including explicit names or auto selection.

    Returns:
        Tuple whose positions are part of the public helper contract shown in the example.

    Examples:
        Input:
            select_healthy_providers(
                configured="AI safety",
            )
        Output:
            ["AI safety", "model evaluation"]
    """
    from social_research_probe.config import load_active_config
    from social_research_probe.utils.core.errors import ValidationError

    cfg = load_active_config()
    if configured == "none" or not cfg.service_enabled("corroboration"):
        return [], ()
    ensure_providers_registered()
    candidates = _candidates(configured)
    healthy: list[str] = []
    for name in candidates:
        if not _llm_search_allowed(name):
            continue
        try:
            if get_provider(name).health_check():
                healthy.append(name)
        except ValidationError:
            pass
    return healthy, candidates


__all__ = [
    "CorroborationProvider",
    "CorroborationResult",
    "aggregate_verdict",
    "auto_mode_providers",
    "corroborate_claim",
    "ensure_providers_registered",
    "get_provider",
    "list_providers",
    "register",
    "select_healthy_providers",
]
