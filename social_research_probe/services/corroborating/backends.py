"""Backend discovery and availability checks for corroboration."""

from social_research_probe.config import Config


def auto_mode_backends(cfg: Config) -> tuple[str, ...]:
    """Return the ordered tuple of backend names to try in auto mode.

    Each backend has its own technology gate; a disabled backend is removed
    from the candidate list without affecting the others.
    """
    return tuple(
        name for name in ("exa", "brave", "tavily", "llm_search") if cfg.technology_enabled(name)
    )
