"""Provider discovery and availability checks for corroboration."""

from social_research_probe.config import Config


def auto_mode_providers(cfg: Config) -> tuple[str, ...]:
    """Return the ordered tuple of provider names to try in auto mode.

    Each provider has its own technology gate; a disabled provider is removed
    from the candidate list without affecting the others.
    """
    return tuple(
        name for name in ("exa", "brave", "tavily", "llm_search") if cfg.technology_enabled(name)
    )
