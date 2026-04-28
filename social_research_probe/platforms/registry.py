"""Module-level registry for platform clients."""

from __future__ import annotations

from social_research_probe.platforms import PlatformClient
from social_research_probe.utils.core.errors import ValidationError
from social_research_probe.utils.core.types import AdapterConfig

CLIENTS: dict[str, type[PlatformClient] | None] = {"all": None}


def register(cls: type[PlatformClient]) -> type[PlatformClient]:
    """Register one platform client class under its declared name."""
    if not hasattr(cls, "name") or not cls.name:
        raise ValueError(f"{cls!r} must define class var `name`")
    CLIENTS[cls.name] = cls
    return cls


def list_clients() -> list[str]:
    """Return names of all registered clients (excludes meta-platforms like 'all')."""
    return [k for k, v in CLIENTS.items() if v is not None]


def get_client(name: str, config: AdapterConfig) -> PlatformClient:
    """Instantiate the named client with the merged runtime config."""
    if name not in CLIENTS:
        known = sorted(CLIENTS.keys())
        raise ValidationError(f"unknown platform: {name!r} (registered: {known})")
    cls = CLIENTS[name]
    if cls is None:
        raise ValidationError(f"platform {name!r} has no dedicated client")
    return cls(config)
