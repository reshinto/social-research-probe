"""LLM service: structured JSON LLM calls via registered runners with fallback."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.services import FallbackService
from social_research_probe.technologies.llms import LLMTech
from social_research_probe.utils.core.types import RunnerName


class LLMService(FallbackService[str, dict]):
    """Structured LLM service: tries runners in priority order until one succeeds."""

    service_name: ClassVar[str] = "llm"
    enabled_config_key: ClassVar[str] = "llm"

    def __init__(self, preferred: RunnerName, schema: dict | None = None) -> None:
        self._preferred = preferred
        self._schema = schema

    def _get_technologies(self) -> list[LLMTech]:
        from social_research_probe.technologies.llms.registry import list_runners

        names = [self._preferred, *[n for n in list_runners() if n != self._preferred]]
        return [LLMTech(n, self._schema) for n in names]
