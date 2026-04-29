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
    """Outcome of a single technology health probe."""

    key: str
    healthy: bool
    message: str


class BaseTechnology(ABC, Generic[TInput, TOutput]):
    """Atomic async adapter: transforms one input into one output.

    Subclasses set class-level ``name``, ``health_check_key``, and
    ``enabled_config_key``, then implement ``_execute``.
    """

    name: ClassVar[str] = ""
    health_check_key: ClassVar[str] = ""
    enabled_config_key: ClassVar[str] = ""
    cacheable: ClassVar[bool] = True

    def __init__(self) -> None:
        self.caller_service: str | None = None

    async def execute(self, data: TInput) -> TOutput | None:
        """Run technology with flag check, timing, and error isolation.

        Returns None on any error or when the technology is disabled.
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
        """Wrap _execute with transparent disk caching.

        Cache resolution: stage disable list → technology default → global disable.
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

        disabled = disable_cache_for_technologies.get() or []
        should_cache = False if self.name in disabled else self.cacheable
        if not should_cache or cache_disabled():
            return await self._execute(data)

        key = self._cache_key(data)
        ttl = TTL_OVERRIDES.get(self.name, DEFAULT_TTL)
        cache = make_cache(f"technologies/{self.name}", ttl)

        cached = get_json(cache, key)
        if cached is not None:
            log(f"[TECH][{self.name}] cache hit")
            return cached

        result = await self._execute(data)

        import contextlib

        if result is not None:
            with contextlib.suppress(TypeError, ValueError):
                set_json(cache, key, result)

        return result

    @abstractmethod
    async def _execute(self, data: TInput) -> TOutput:
        """Perform the actual technology operation."""

    async def health_check(self) -> HealthCheckResult:
        """Return health status; subclasses override for real checks."""
        return HealthCheckResult(
            key=self.health_check_key,
            healthy=True,
            message="ok",
        )

    def _cache_key(self, data: TInput) -> str:
        """Stable cache key derived from the input repr."""
        return hashlib.sha256(repr(data).encode()).hexdigest()
