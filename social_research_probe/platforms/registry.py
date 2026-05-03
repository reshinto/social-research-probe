"""Module-level registry for platform clients."""

from __future__ import annotations

from social_research_probe.platforms import PlatformClient
from social_research_probe.utils.core.errors import ValidationError
from social_research_probe.utils.core.types import AdapterConfig

CLIENTS: dict[str, type[PlatformClient] | None] = {"all": None}


def register(cls: type[PlatformClient]) -> type[PlatformClient]:
    """Register the implementation in the module registry.

    Platform orchestration code uses this contract to run different platforms without leaking
    platform-specific state into callers.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            register()
        Output:
            "AI safety"
    """
    if not hasattr(cls, "name") or not cls.name:
        raise ValueError(f"{cls!r} must define class var `name`")
    CLIENTS[cls.name] = cls
    return cls


def list_clients() -> list[str]:
    """Return names of all registered clients (excludes meta-platforms like 'all').

    Platform orchestration code uses this contract to run different platforms without leaking
    platform-specific state into callers.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            list_clients()
        Output:
            ["AI safety", "model evaluation"]
    """
    return [k for k, v in CLIENTS.items() if v is not None]


def get_client(name: str, config: AdapterConfig) -> PlatformClient:
    """Return the registered platform client requested by configuration.

    Platform orchestration code uses this contract to run different platforms without leaking
    platform-specific state into callers.

    Args:
        name: Registry, config, or CLI name used to select the matching project value.
        config: Configuration or context values that control this run.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            get_client(
                name="AI safety",
                config={"enabled": True},
            )
        Output:
            "AI safety"
    """
    if name not in CLIENTS:
        known = sorted(CLIENTS.keys())
        raise ValidationError(f"unknown platform: {name!r} (registered: {known})")
    cls = CLIENTS[name]
    if cls is None:
        raise ValidationError(f"platform {name!r} has no dedicated client")
    return cls(config)
