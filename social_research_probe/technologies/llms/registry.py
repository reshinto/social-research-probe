"""Registry for LLM runner implementations.

Why this exists: provides a central lookup table so the pipeline can request a
runner by name (e.g. "claude") and receive a ready-to-use instance without
importing vendor-specific modules directly.

Who calls it: technologies/llms/__init__.py (to trigger registration), the
pipeline, the corroboration host, and CLI commands that need to select a runner.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from social_research_probe.technologies.llms.base import LLMRunner
from social_research_probe.utils.core.errors import ValidationError

if TYPE_CHECKING:
    from social_research_probe.utils.core.types import RunnerName

# Maps runner name strings (e.g. "claude") to their concrete class objects.
# Populated at import time as each runners/*.py module is loaded.
_REGISTRY: dict[str, type[LLMRunner]] = {}


def register(cls: type[LLMRunner]) -> type[LLMRunner]:
    """Class decorator that adds a runner class to the registry.

    Stores cls under cls.name so get_runner() can find it later. Designed to
    be used as @register on each concrete LLMRunner subclass.

    Args:
        cls: The LLMRunner subclass to register. Must define a non-empty
            class variable ``name``.

    Returns:
        cls unchanged (so the decorator is transparent to the class definition).

    Raises:
        ValueError: If cls does not define a non-empty ``name`` class variable.
    """
    if not hasattr(cls, "name") or not cls.name:
        raise ValueError(f"{cls!r} must define class var `name`")
    _REGISTRY[cls.name] = cls
    return cls


def get_runner(name: str) -> LLMRunner:
    """Instantiate and return the runner registered under name.

    Args:
        name: The runner key to look up (e.g. "claude", "gemini").

    Returns:
        A fresh instance of the corresponding LLMRunner subclass.

    Raises:
        ValidationError: If name is not present in the registry.
    """
    if name not in _REGISTRY:
        known = sorted(_REGISTRY.keys())
        raise ValidationError(f"unknown LLM runner: {name!r} (registered: {known})")
    return _REGISTRY[name]()


def list_runners() -> list[str]:
    """Return a sorted list of all registered runner names.

    Returns:
        Sorted list of name strings (e.g. ["claude", "codex", "gemini", "local"]).
    """
    return sorted(_REGISTRY.keys())


def run_with_fallback(prompt: str, schema: dict, preferred: RunnerName) -> dict:
    """Try runners in priority order, skip unhealthy ones, return first success.

    Implements resilient runner orchestration: prefers the specified runner but
    falls back to others if health checks fail or execution raises exceptions.

    Args:
        prompt: Input prompt to send to the runner.
        schema: JSON schema for structured output validation.
        preferred: Preferred runner name (tried first).

    Returns:
        The first successful classification result dict.

    Raises:
        ValidationError: If all runners are unhealthy or fail execution.
    """
    candidates = list_runners()
    runner_order = [preferred, *[n for n in candidates if n != preferred]]

    for name in runner_order:
        runner = get_runner(name)
        if not runner.health_check():
            continue
        try:
            return runner.run(prompt, schema=schema)
        except Exception:
            continue

    raise ValidationError(
        "unable to run LLM: all runners are unhealthy or failed. "
        "Check runner health and try again."
    )
