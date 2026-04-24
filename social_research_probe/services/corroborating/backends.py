"""Backend discovery and availability checks for corroboration."""

from pathlib import Path

from social_research_probe.config import Config
from social_research_probe.utils.core.errors import ValidationError
from social_research_probe.utils.display.progress import log

from .registry import get_backend


def auto_mode_backends(cfg: Config) -> tuple[str, ...]:
    """Return the ordered tuple of backend names to try in auto mode.

    Each backend has its own technology gate; a disabled backend is removed
    from the candidate list without affecting the others.
    """
    return tuple(
        name for name in ("exa", "brave", "tavily", "llm_search") if cfg.technology_enabled(name)
    )


def available_backends(data_dir: Path, cfg=None) -> list[str]:
    """Return corroboration backends allowed by config and available at runtime.

    ``backend = auto`` auto-discovers the configured search backends whose
    credentials or runner capabilities are usable. A specific backend value
    uses only that backend. ``backend = none`` disables corroboration entirely.
    """
    if cfg is None:
        cfg = Config.load(data_dir)
    configured = cfg.corroboration_backend
    if not cfg.stage_enabled("corroborate"):
        log("[srp] corroboration: disabled by stages.corroborate = false.")
        return []
    if not cfg.service_enabled("corroboration"):
        log("[srp] corroboration: disabled by services.corroboration = false.")
        return []
    if configured == "none":
        log(
            "[srp] corroboration: disabled in config (corroboration.backend = 'none'). Enable with 'srp config set corroboration.backend auto'."
        )
        return []
    auto_candidates = auto_mode_backends(cfg)
    candidates = auto_candidates if configured == "auto" else (configured,)

    available: list[str] = []
    for name in candidates:
        if not cfg.technology_enabled(name):
            continue
        if name == "llm_search" and not cfg.service_enabled("llm"):
            continue
        try:
            if get_backend(name).health_check():
                available.append(name)
        except ValidationError:
            pass

    if not available:
        checked = ", ".join(candidates)
        log(
            f"[srp] corroboration: backend '{configured}' configured but no provider usable"
            f" (checked: {checked}). Hint: run 'srp config check-secrets --corroboration {configured}'."
        )
    return available
