"""Registry for corroboration backend implementations.

What: Maintains a global dict mapping backend names to their classes and
provides helpers to register, look up, and list them.

Why: Decouples the host and CLI from concrete backend imports — a new backend
only needs to call @register to become discoverable.

Who calls it: backend modules (use @register decorator at class definition time),
host.py (calls get_backend()), and CLI commands that want to list available backends.
"""

from __future__ import annotations

from social_research_probe.corroboration.base import CorroborationBackend
from social_research_probe.errors import ValidationError

# Mapping from backend name string to the backend class (not instance).
# Populated at import time by the @register decorator.
_REGISTRY: dict[str, type[CorroborationBackend]] = {}


def canonical_backend_name(name: str) -> str:
    """Return the canonical backend key for ``name``.

    ``llm_cli`` is kept as a legacy alias for backward compatibility with
    older configs and commands, but the canonical runner-backed web-search
    backend is now ``llm_search``.
    """
    return "llm_search" if name == "llm_cli" else name


def register(cls: type[CorroborationBackend]) -> type[CorroborationBackend]:
    """Class decorator that adds cls to the global registry.

    Args:
        cls: A CorroborationBackend subclass that defines a non-empty class
            variable ``name``.

    Returns:
        cls unchanged, so the decorator can be stacked or used transparently.

    Raises:
        ValueError: if cls does not define a non-empty ``name`` class variable,
            which would make the backend un-addressable.
    """
    if not hasattr(cls, "name") or not cls.name:
        raise ValueError(f"{cls!r} must define class var `name`")
    _REGISTRY[cls.name] = cls
    return cls


def get_backend(name: str) -> CorroborationBackend:
    """Instantiate and return the named backend.

    Args:
        name: The string key used when the backend called @register, e.g.
            "exa", "brave", "tavily", or "llm_search". Legacy callers may
            still pass ``"llm_cli"``, which resolves to ``"llm_search"``.

    Returns:
        A fresh instance of the corresponding CorroborationBackend subclass.

    Raises:
        ValidationError: if name is not in the registry. The error message
            lists the known backend names so callers can self-correct.
    """
    canonical = canonical_backend_name(name)
    if canonical not in _REGISTRY:
        known = sorted(_REGISTRY.keys())
        raise ValidationError(f"unknown corroboration backend: {name!r} (registered: {known})")
    return _REGISTRY[canonical]()


def list_backends() -> list[str]:
    """Return a sorted list of registered backend names.

    Returns:
        Alphabetically sorted list of name strings, matching the keys of
        _REGISTRY at call time.
    """
    return sorted(_REGISTRY.keys())
