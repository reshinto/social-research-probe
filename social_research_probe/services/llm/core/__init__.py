"""LLM service: structured JSON LLM calls via registered runners with fallback."""

from __future__ import annotations

import asyncio
from typing import ClassVar

from social_research_probe.services import FallbackService
from social_research_probe.technologies.base import BaseTechnology
from social_research_probe.utils.core.types import RunnerName


class LLMTech(BaseTechnology[str, dict]):
    """Technology adapter wrapping one registered LLM runner for structured JSON calls."""

    enabled_config_key: ClassVar[str] = ""

    def __init__(self, runner_name: str, schema: dict | None = None) -> None:
        super().__init__()
        self._runner_name = runner_name
        self._schema = schema

    @property
    def name(self) -> str:  # type: ignore[override]
        return f"llm.{self._runner_name}"

    async def _execute(self, prompt: str) -> dict | None:
        from social_research_probe.services.llm.core.helpers.registry import get_runner

        runner = get_runner(self._runner_name)
        if not runner.health_check():
            return None
        return await asyncio.to_thread(runner.run, prompt, schema=self._schema)


class LLMService(FallbackService[str, dict]):
    """Structured LLM service: tries runners in priority order until one succeeds."""

    service_name: ClassVar[str] = "llm"
    enabled_config_key: ClassVar[str] = "llm"

    def __init__(self, preferred: RunnerName, schema: dict | None = None) -> None:
        self._preferred = preferred
        self._schema = schema

    def _get_technologies(self) -> list[BaseTechnology]:
        from social_research_probe.services.llm.core.helpers.registry import list_runners

        names = [self._preferred, *[n for n in list_runners() if n != self._preferred]]
        return [LLMTech(n, self._schema) for n in names]
