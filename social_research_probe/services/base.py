"""Abstract base service: concurrent batch execution over technologies."""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import ClassVar, Generic, TypeVar

from social_research_probe.technologies.base import BaseTechnology
from social_research_probe.utils.display.progress import log_with_time

TInput = TypeVar("TInput")
TOutput = TypeVar("TOutput")


@dataclass
class TechResult:
    """Outcome of one technology execution within a service call."""

    tech_name: str
    input: object
    output: object
    success: bool
    error: str | None = None


@dataclass
class ServiceResult:
    """Aggregated output from one service execute_one call."""

    service_name: str
    input_key: str
    tech_results: list[TechResult] = field(default_factory=list)


class BaseService(ABC, Generic[TInput, TOutput]):
    """Runs a batch of inputs through technologies concurrently.

    Subclasses set ``service_name`` and ``enabled_config_key``, then
    implement ``_get_technologies`` to return the tech instances to run.
    """

    service_name: ClassVar[str] = ""
    enabled_config_key: ClassVar[str] = ""

    async def execute_batch(
        self,
        inputs: list[TInput],
    ) -> list[ServiceResult]:
        """Run all inputs concurrently; return one ServiceResult per input."""
        results = await asyncio.gather(
            *(self.execute_one(item) for item in inputs),
        )
        return list(results)

    @log_with_time("[srp] {self.service_name}: execute_one")
    async def execute_one(
        self,
        data: TInput,
    ) -> ServiceResult:
        """Run all technologies for one input; isolate per-technology errors."""
        techs = self._get_technologies()

        async def _run(tech: BaseTechnology) -> TechResult:
            tech.caller_service = self.service_name
            try:
                output = await tech.execute(data)
                return TechResult(
                    tech_name=tech.name,
                    input=data,
                    output=output,
                    success=output is not None,
                )
            except Exception as exc:
                return TechResult(
                    tech_name=tech.name,
                    input=data,
                    output=None,
                    success=False,
                    error=str(exc),
                )

        tech_results = list(await asyncio.gather(*(_run(t) for t in techs)))
        return ServiceResult(
            service_name=self.service_name,
            input_key=repr(data),
            tech_results=tech_results,
        )

    @abstractmethod
    def _get_technologies(self) -> list[BaseTechnology]:
        """Return technology instances to run for one input."""
