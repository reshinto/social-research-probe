"""Abstract base service: protected batch/one execution over service logic."""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import ClassVar, Generic, TypeVar

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
    """Runs inputs through service-specific logic via a protected lifecycle.

    Subclasses set ``service_name`` and ``enabled_config_key``, then implement
    ``execute_service``. They must not override ``execute_batch`` or
    ``execute_one``; those methods are the framework contract used by pipelines.
    """

    service_name: ClassVar[str] = ""
    enabled_config_key: ClassVar[str] = ""
    run_technologies_concurrently: ClassVar[bool] = True

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        forbidden = {"execute_batch", "execute_one"}.intersection(cls.__dict__)
        if forbidden:
            names = ", ".join(sorted(forbidden))
            raise TypeError(
                f"{cls.__name__} must implement execute_service; "
                f"do not override protected BaseService method(s): {names}"
            )

    @classmethod
    def is_enabled(cls) -> bool:
        """Return True iff this service's feature flag is enabled."""
        from social_research_probe.config import load_active_config

        if not cls.enabled_config_key:
            return True
        leaf = cls.enabled_config_key.rsplit(".", 1)[-1]
        return load_active_config().service_enabled(leaf)

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
        """Run one input through this service's implementation."""
        if not self.is_enabled():
            return ServiceResult(
                service_name=self.service_name,
                input_key=repr(data),
                tech_results=[],
            )
        return await self._execute_technologies_concurrently(data)

    @abstractmethod
    async def execute_service(
        self,
        data: TInput,
        result: ServiceResult,
    ) -> ServiceResult:
        """Apply service-specific logic to the framework technology result."""

    async def _execute_technologies_concurrently(
        self,
        data: TInput,
    ) -> ServiceResult:
        """Run all technologies for one input; isolate per-technology errors."""
        techs = self._get_technologies()
        if not techs:
            raise ValueError(
                f"{self.__class__.__name__}._get_technologies() must return technology "
                "instances, or [None] when the service has no technology layer."
            )
        tech_input = self._technology_input(data)
        result = ServiceResult(
            service_name=self.service_name,
            input_key=repr(tech_input),
            tech_results=[],
        )
        if techs == [None] or not self.run_technologies_concurrently:
            return await self.execute_service(data, result)

        async def _run(tech: object) -> TechResult:
            tech.caller_service = self.service_name

            try:
                output = await tech.execute(tech_input)
                return TechResult(
                    tech_name=tech.name,
                    input=tech_input,
                    output=output,
                    success=output is not None,
                )
            except Exception as exc:
                return TechResult(
                    tech_name=tech.name,
                    input=tech_input,
                    output=None,
                    success=False,
                    error=str(exc),
                )

        result = ServiceResult(
            service_name=self.service_name,
            input_key=repr(tech_input),
            tech_results=list(await asyncio.gather(*(_run(t) for t in techs))),
        )
        return await self.execute_service(data, result)

    def _technology_input(self, data: TInput) -> object:
        """Return the value passed to technology adapters."""
        return data

    @abstractmethod
    def _get_technologies(self) -> list[object]:
        """Return technology instances to run for one input."""
