"""Module-level registry for platform adapters."""

from __future__ import annotations

from social_research_probe.errors import ValidationError
from social_research_probe.platforms.base import PlatformAdapter
from social_research_probe.types import AdapterConfig

_REGISTRY: dict[str, type[PlatformAdapter]] = {}


def register(cls: type[PlatformAdapter]) -> type[PlatformAdapter]:
    """Register one platform adapter class under its declared name."""
    if not hasattr(cls, "name") or not cls.name:
        raise ValueError(f"{cls!r} must define class var `name`")
    _REGISTRY[cls.name] = cls
    return cls


def get_adapter(name: str, config: AdapterConfig) -> PlatformAdapter:
    """Instantiate the named adapter with the merged runtime config."""
    if name not in _REGISTRY:
        known = sorted(_REGISTRY.keys())
        raise ValidationError(f"unknown platform: {name!r} (registered: {known})")
    return _REGISTRY[name](config)


def list_adapters() -> list[str]:
    """Return the registered adapter names in deterministic order."""
    return sorted(_REGISTRY.keys())
