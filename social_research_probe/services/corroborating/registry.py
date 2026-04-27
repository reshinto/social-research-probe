"""Registry for corroboration provider implementations.

What: Maintains a global dict mapping provider names to their classes and
provides helpers to register, look up, and list them.

Why: Decouples the host and CLI from concrete provider imports — a new provider
only needs to call @register to become discoverable.

Who calls it: provider modules (use @register decorator at class definition time),
host.py (calls get_provider()), and CLI commands that want to list available providers.
"""

from __future__ import annotations

from social_research_probe.technologies.corroborates.base import CorroborationProvider
from social_research_probe.utils.core.errors import ValidationError

# Mapping from provider name string to the provider class (not instance).
# Populated at import time by the @register decorator.
_REGISTRY: dict[str, type[CorroborationProvider]] = {}


def register(cls: type[CorroborationProvider]) -> type[CorroborationProvider]:
    """Class decorator that adds cls to the global registry.

    Args:
        cls: A CorroborationProvider subclass that defines a non-empty class
            variable ``name``.

    Returns:
        cls unchanged, so the decorator can be stacked or used transparently.

    Raises:
        ValueError: if cls does not define a non-empty ``name`` class variable,
            which would make the provider un-addressable.
    """
    if not hasattr(cls, "name") or not cls.name:
        raise ValueError(f"{cls!r} must define class var `name`")
    _REGISTRY[cls.name] = cls
    return cls


def get_provider(name: str) -> CorroborationProvider:
    """Instantiate and return the named provider.

    Args:
        name: The string key used when the provider called @register, e.g.
            "exa", "brave", "tavily", or "llm_search".

    Returns:
        A fresh instance of the corresponding CorroborationProvider subclass.

    Raises:
        ValidationError: if name is not in the registry. The error message
            lists the known provider names so callers can self-correct.
    """
    if name not in _REGISTRY:
        known = sorted(_REGISTRY.keys())
        raise ValidationError(f"unknown corroboration provider: {name!r} (registered: {known})")
    return _REGISTRY[name]()


def list_providers() -> list[str]:
    """Return a sorted list of registered provider names.

    Returns:
        Alphabetically sorted list of name strings, matching the keys of
        _REGISTRY at call time.
    """
    return sorted(_REGISTRY.keys())


def ensure_providers_registered() -> None:
    """Import concrete corroboration provider modules so their @register
    decorators run. Must be called once during process bootstrap.

    Uses importlib to break the import cycle: this module sits below
    technologies/corroborates/* in the dependency graph, so a top-of-file
    import would create a loop.
    """
    import importlib

    for module in ("exa", "brave", "tavily", "llm_search"):
        try:
            importlib.import_module(f"social_research_probe.technologies.corroborates.{module}")
        except ImportError:
            continue
