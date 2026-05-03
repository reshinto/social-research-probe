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

    This decorator adds each concrete runner class to the shared registry under its class-
    level ``name`` value. That lets orchestration code look up runners dynamically instead
    of hard-coding specific classes.

    Returns:
        Normalized value needed by the next operation.

    Raises:
                        ValueError: If the runner does not define a non-empty ``name``.




    Examples:
        Input:
            register()
        Output:
            "AI safety"
    """
    if not hasattr(cls, "name") or not cls.name:
        raise ValueError(f"{cls!r} must define class var `name`")
    _REGISTRY[cls.name] = cls
    return cls


def get_runner(name: str) -> LLMRunner:
    """Create the runner selected by name.

    Looks up the requested runner in the registry and returns a fresh instance. This keeps
    callers decoupled from concrete runner classes and centralizes validation of supported
    runner names.

    Args:
        name: Registry, config, or CLI name used to select the matching project value.

    Returns:
        Normalized value needed by the next operation.

    Raises:
                        ValidationError: If no runner has been registered with that name.




    Examples:
        Input:
            get_runner(
                name="codex",
            )
        Output:
            "AI safety"
    """
    from social_research_probe.config import load_active_config

    if name not in _REGISTRY:
        known = sorted(_REGISTRY.keys())
        raise ValidationError(f"unknown LLM runner: {name!r} (registered: {known})")
    if not load_active_config().technology_enabled(name):
        raise ValidationError(f"LLM runner {name!r} is not enabled in [technologies]")
    return _REGISTRY[name]()


def list_runners() -> list[str]:
    """Return enabled runner names in the order they should be tried.

    Filters the registry against the active config's ``technology_enabled``
    gate so only runners explicitly enabled in ``[technologies]`` are
    returned. The preferred runner is placed first so callers can attempt it
    before falling back to the remaining enabled runners.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            list_runners()
        Output:
            ["AI safety", "model evaluation"]
    """
    from social_research_probe.config import load_active_config

    cfg = load_active_config()
    return sorted(name for name in _REGISTRY if cfg.technology_enabled(name))


def prioritize_runner(candidates: list[RunnerName], preferred: RunnerName) -> list[RunnerName]:
    """Return runner names with the preferred runner first.

    This utility is shared across commands, services, and stages, so the rule lives here instead of
    being reimplemented differently at each call site.

    Args:
        candidates: Ordered source items being carried through the current pipeline step.
        preferred: Provider or runner selected for this operation.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            prioritize_runner(
                candidates=[{"title": "Example", "url": "https://youtu.be/demo"}],
                preferred="codex",
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
    """
    return [preferred, *[n for n in candidates if n != preferred]]


def run_with_fallback(prompt: str, schema: dict, preferred: RunnerName) -> dict:
    """Run the prompt using the preferred runner, then fallback runners.

    The preferred runner is tried first so caller intent is respected. Remaining registered
    runners are tried afterward, excluding the preferred runner to avoid duplicate attempts.

    Unhealthy runners and runners that raise during execution are skipped so another
    available runner can still handle the request.

    Args:
        prompt: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
                to a provider.
        schema: JSON schema that the LLM or validator must satisfy.
        preferred: Provider or runner selected for this operation.

    Returns:
        Dictionary with stable keys consumed by downstream project code.

    Raises:
                        ValidationError: If every runner is unhealthy or fails execution.




    Examples:
        Input:
            run_with_fallback(
                prompt="Summarize this source.",
                schema={"enabled": True},
                preferred="codex",
            )
        Output:
            {"enabled": True}
    """
    candidates = list_runners()
    if preferred in candidates:
        runner_order = [preferred, *[n for n in candidates if n != preferred]]
    else:
        runner_order = candidates

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


def ensure_runners_registered() -> None:
    """Import concrete LLM runner modules so their @register decorators run.

    This utility is shared across commands, services, and stages, so the rule lives here instead of
    being reimplemented differently at each call site.

    Returns:
        None. The result is communicated through state mutation, file/database writes, output, or an
        exception.

    Examples:
        Input:
            ensure_runners_registered()
        Output:
            None
    """
    import importlib

    for module in ("claude_cli", "codex_cli", "gemini_cli"):
        importlib.import_module(f"social_research_probe.technologies.llms.{module}")
