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

# ---------------------------------------------------------------------------
# Provider helpers
# ---------------------------------------------------------------------------


def auto_mode_providers() -> tuple[str, ...]:
    """Return ordered provider names to try in auto mode."""
    from social_research_probe.config import load_active_config

    cfg = load_active_config()
    return tuple(
        name for name in ("exa", "brave", "tavily", "llm_search") if cfg.technology_enabled(name)
    )


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
]
