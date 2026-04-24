"""Registry for LLM runner implementations.

Why this exists: provides a central lookup table so the pipeline can request a
runner by name (e.g. "claude") and receive a ready-to-use instance without
importing vendor-specific modules directly.

Who calls it: technologies/llms/__init__.py (to trigger registration), the
pipeline, the corroboration host, and CLI commands that need to select a runner.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from social_research_probe.technologies.llms import LLMRunner
from social_research_probe.utils.core.errors import ValidationError

if TYPE_CHECKING:
    from social_research_probe.utils.core.types import RunnerName

# Maps runner name strings (e.g. "claude") to their concrete class objects.
# Populated at import time as each runners/*.py module is loaded.
_REGISTRY: dict[str, type[LLMRunner]] = {}


def register(cls: type[LLMRunner]) -> type[LLMRunner]:
    """Register an LLMRunner implementation so it can be selected by name.

    This decorator adds each concrete runner class to the shared registry under
    its class-level ``name`` value. That lets orchestration code look up runners
    dynamically instead of hard-coding specific classes.

    Args:
        cls: LLMRunner subclass to register. Must define a non-empty ``name``.

    Returns:
        The same class unchanged, so this can be used transparently as
        ``@register``.

    Raises:
        ValueError: If the runner does not define a non-empty ``name``.
    """
    if not hasattr(cls, "name") or not cls.name:
        raise ValueError(f"{cls!r} must define class var `name`")
    _REGISTRY[cls.name] = cls
    return cls


def get_runner(name: str) -> LLMRunner:
    """Create the runner selected by name.

    Looks up the requested runner in the registry and returns a fresh instance.
    This keeps callers decoupled from concrete runner classes and centralizes
    validation of supported runner names.

    Args:
        name: Registered runner name, such as ``"claude"`` or ``"gemini"``.

    Returns:
        A new instance of the matching LLMRunner subclass.

    Raises:
        ValidationError: If no runner has been registered with that name.
    """
    if name not in _REGISTRY:
        known = sorted(_REGISTRY.keys())
        raise ValidationError(f"unknown LLM runner: {name!r} (registered: {known})")
    return _REGISTRY[name]()


def list_runners() -> list[str]:
    """Return runner names in the order they should be tried.

    The preferred runner is placed first so callers can attempt it before
    falling back to the remaining registered runners. The preferred runner is
    excluded from the fallback portion to avoid trying it twice.

    Returns:
        Ordered list of runner name strings.
    """
    return sorted(_REGISTRY.keys())


def run_with_fallback(prompt: str, schema: dict, preferred: RunnerName) -> dict:
    """Run the prompt using the preferred runner, then fallback runners.

    The preferred runner is tried first so caller intent is respected. Remaining
    registered runners are tried afterward, excluding the preferred runner to
    avoid duplicate attempts. Unhealthy runners and runners that raise during
    execution are skipped so another available runner can still handle the
    request.

    Args:
        prompt: Input prompt to send to the runner.
        schema: JSON schema used to request structured output.
        preferred: Runner to try before all fallback runners.

    Returns:
        The first successful runner result.

    Raises:
        ValidationError: If every runner is unhealthy or fails execution.
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
        "unable to run LLM: all runners are unhealthy or failed. Check runner health and try again."
    )
