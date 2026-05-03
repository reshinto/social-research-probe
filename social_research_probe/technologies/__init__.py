"""Atomic async technology adapters: single input → single output.

Internal package; BaseTechnology is for use within technologies/ folder only.
"""

import hashlib
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar, Generic, TypeVar

from social_research_probe.config import load_active_config
from social_research_probe.utils.display.progress import log

__all__ = []

TInput = TypeVar("TInput")
TOutput = TypeVar("TOutput")


@dataclass
class HealthCheckResult:
    """Outcome of a single technology health probe.

    Keeping these fields together makes pipeline handoffs easier to inspect and harder to
    accidentally reorder.

    Examples:
        Input:
            HealthCheckResult
        Output:
            HealthCheckResult(key="codex", healthy=True, message="available")
    """

    key: str
    healthy: bool
    message: str


class BaseTechnology(ABC, Generic[TInput, TOutput]):
    """Atomic async adapter: transforms one input into one output.

    Subclasses set class-level ``name``, ``health_check_key``, and ``enabled_config_key``,
    then implement ``_execute``.

    Examples:
        Input:
            BaseTechnology
        Output:
            BaseTechnology
    """

    name: ClassVar[str] = ""
    health_check_key: ClassVar[str] = ""
    enabled_config_key: ClassVar[str] = ""
    cacheable: ClassVar[bool] = True

    def __init__(self) -> None:
        """Store constructor options used by later method calls.

        Returns:
            None. The result is communicated through state mutation, file/database writes, output, or an
            exception.

        Examples:
            Input:
                __init__()
            Output:
                None
        """
        self.caller_service: str | None = None

    async def execute(self, data: TInput) -> TOutput | None:
        """Run technology with flag check, timing, and error isolation.

        Returns None on any error or when the technology is disabled.

        Args:
            data: Input payload at this service, technology, or pipeline boundary.

        Returns:
            Normalized value needed by the next operation.

        Examples:
            Input:
                await execute(
                    data={"title": "Example", "url": "https://youtu.be/demo"},
                )
            Output:
                "AI safety"
        """
        cfg = load_active_config()
        if self.enabled_config_key and not cfg.technology_enabled(self.enabled_config_key):
            return None
        caller = self.caller_service or "?"
        label = f"[TECH][{self.name}]"
        if cfg.debug_enabled("pipeline"):
            log(f"{label} called_by={caller} -- starting")
        start = time.monotonic()
        try:
            result = await self._cached_execute(data)
        except Exception as exc:
            log(f"{label} error: {exc}")
            return None
        if cfg.debug_enabled("pipeline"):
            log(f"{label} done in {time.monotonic() - start:.2f}s")
        return result

    async def _cached_execute(self, data: TInput) -> TOutput:
        """Document the cached execute rule at the boundary where callers use it.

        The helper keeps a small project rule named and documented at the boundary where it is used.

        Args:
            data: Input payload at this service, technology, or pipeline boundary.

        Returns:
            Normalized value needed by the next operation.

        Examples:
            Input:
                await _cached_execute(
                    data={"title": "Example", "url": "https://youtu.be/demo"},
                )
            Output:
                "AI safety"
        """
        from social_research_probe.utils.caching.pipeline_cache import (
            DEFAULT_TTL,
            TTL_OVERRIDES,
            cache_disabled,
            disable_cache_for_technologies,
            get_json,
            make_cache,
            set_json,
        )

        cfg = load_active_config()
        debug = cfg.debug_enabled("pipeline")

        disabled = disable_cache_for_technologies.get() or []
        if self.name in disabled:
            if debug:
                log(f"[TECH][{self.name}] cache bypass: stage disabled")
            return await self._execute(data)
        if not self.cacheable:
            if debug:
                log(f"[TECH][{self.name}] cache bypass: not cacheable")
            return await self._execute(data)
        if cache_disabled():
            if debug:
                log(f"[TECH][{self.name}] cache bypass: SRP_DISABLE_CACHE")
            return await self._execute(data)

        key = self._cache_key(data)
        ttl = TTL_OVERRIDES.get(self.name, DEFAULT_TTL)
        cache = make_cache(f"technologies/{self.name}", ttl)

        cached = get_json(cache, key)
        if isinstance(cached, dict) and "output" in cached:
            log(f"[TECH][{self.name}] cache hit")
            return cached["output"]
        if debug:
            log(f"[TECH][{self.name}] cache miss — calling _execute")

        result = await self._execute(data)

        if result is not None:
            set_json(cache, key, {"input": repr(data), "output": result})
            if debug:
                log(f"[TECH][{self.name}] cache write ok")
        elif debug:
            log(f"[TECH][{self.name}] _execute returned None — not cached")

        return result

    @abstractmethod
    async def _execute(self, data: TInput) -> TOutput:
        """Run this component and return the project-shaped output expected by its service.

        The helper keeps a small project rule named and documented at the boundary where it is used.

        Args:
            data: Input payload at this service, technology, or pipeline boundary.

        Returns:
            Normalized value needed by the next operation.

        Examples:
            Input:
                await _execute(
                    data={"title": "Example", "url": "https://youtu.be/demo"},
                )
            Output:
                "AI safety"
        """

    async def health_check(self) -> HealthCheckResult:
        """Report whether this client or provider is usable before it is selected.

        The helper keeps a small project rule named and documented at the boundary where it is used.

        Returns:
            HealthCheckResult with the checked key, status, and operator-facing message.

        Examples:
            Input:
                await health_check()
            Output:
                HealthCheckResult(key="codex", healthy=True, message="available")
        """
        return HealthCheckResult(
            key=self.health_check_key,
            healthy=True,
            message="ok",
        )

    def _cache_key(self, data: TInput) -> str:
        """Stable cache key derived from the input repr.

        Args:
            data: Input payload at this service, technology, or pipeline boundary.

        Returns:
            Normalized string used as a config key, provider value, or report field.

        Examples:
            Input:
                _cache_key(
                    data={"title": "Example", "url": "https://youtu.be/demo"},
                )
            Output:
                "AI safety"
        """
        return hashlib.sha256(repr(data).encode()).hexdigest()
