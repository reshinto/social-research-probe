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
    """Outcome of one technology execution within a service call.

    Keeping these fields together makes pipeline handoffs easier to inspect and harder to
    accidentally reorder.

    Examples:
        Input:
            TechResult
        Output:
            TechResult
    """

    tech_name: str
    input: object
    output: object
    success: bool
    error: str | None = None


@dataclass
class ServiceResult:
    """Aggregated output from one service execute_one call.

    Keeping these fields together makes pipeline handoffs easier to inspect and harder to
    accidentally reorder.

    Examples:
        Input:
            ServiceResult
        Output:
            ServiceResult
    """

    service_name: str
    input_key: str
    tech_results: list[TechResult] = field(default_factory=list)


class BaseService(ABC, Generic[TInput, TOutput]):
    """Runs inputs through service-specific logic via a protected lifecycle.

    Subclasses set ``service_name`` and ``enabled_config_key``, then implement ``execute_service``.
    They must not override ``execute_batch`` or ``execute_one``; those methods are the framework
    contract used by pipelines.

    Examples:
        Input:
            BaseService
        Output:
            BaseService
    """

    service_name: ClassVar[str] = ""
    enabled_config_key: ClassVar[str] = ""
    run_technologies_concurrently: ClassVar[bool] = True

    def __init_subclass__(cls, **kwargs):
        """Document the init subclass rule at the boundary where callers use it.

        Services translate platform data into adapter calls and normalize the result so stages can
        handle success, skip, and failure consistently.

        Returns:
            Normalized value needed by the next operation.

        Examples:
            Input:
                __init_subclass__()
            Output:
                "AI safety"
        """
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
        """Return True iff this service's feature flag is enabled.

        Returns:
            True when the condition is satisfied; otherwise False.

        Examples:
            Input:
                BaseService.is_enabled()
            Output:
                True
        """
        from social_research_probe.config import load_active_config

        if not cls.enabled_config_key:
            return True
        leaf = cls.enabled_config_key.rsplit(".", 1)[-1]
        return load_active_config().service_enabled(leaf)

    async def execute_batch(
        self,
        inputs: list[TInput],
    ) -> list[ServiceResult]:
        """Run all inputs concurrently; return one ServiceResult per input.

        Services translate platform data into adapter calls and normalize the result so stages can
        handle success, skip, and failure consistently.

        Args:
            inputs: Batch input payloads that will each become a ServiceResult.

        Returns:
            ServiceResult containing normalized output plus per-technology diagnostics.

        Examples:
            Input:
                await execute_batch(
                    inputs=["AI safety"],
                )
            Output:
                ServiceResult(service_name="summary", input_key="demo", tech_results=[])
        """
        results = await asyncio.gather(
            *(self.execute_one(item) for item in inputs),
        )
        return list(results)

    @log_with_time("[srp] {self.service_name}: execute_one")
    async def execute_one(
        self,
        data: TInput,
    ) -> ServiceResult:
        """Run one input through this service's implementation.

        Services translate platform data into adapter calls and normalize the result so stages can
        handle success, skip, and failure consistently.

        Args:
            data: Input payload at this service, technology, or pipeline boundary.

        Returns:
            ServiceResult containing normalized output plus per-technology diagnostics.

        Examples:
            Input:
                await execute_one(
                    data={"title": "Example", "url": "https://youtu.be/demo"},
                )
            Output:
                ServiceResult(service_name="summary", input_key="demo", tech_results=[])
        """
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
        """Apply service-specific logic to the framework technology result.

        Services translate platform data into adapter calls and normalize the result so stages can
        handle success, skip, and failure consistently.

        Args:
            data: Input payload at this service, technology, or pipeline boundary.
            result: Service or technology result being inspected for payload and diagnostics.

        Returns:
            ServiceResult containing normalized output plus per-technology diagnostics.

        Examples:
            Input:
                await execute_service(
                    data={"title": "Example", "url": "https://youtu.be/demo"},
                    result=ServiceResult(service_name="comments", input_key="demo", tech_results=[]),
                )
            Output:
                ServiceResult(service_name="summary", input_key="demo", tech_results=[])
        """

    async def _execute_technologies_concurrently(
        self,
        data: TInput,
    ) -> ServiceResult:
        """Run all technologies for one input; isolate per-technology errors.

        Services translate platform data into adapter calls and normalize the result so stages can
        handle success, skip, and failure consistently.

        Args:
            data: Input payload at this service, technology, or pipeline boundary.

        Returns:
            ServiceResult containing normalized output plus per-technology diagnostics.

        Examples:
            Input:
                await _execute_technologies_concurrently(
                    data={"title": "Example", "url": "https://youtu.be/demo"},
                )
            Output:
                ServiceResult(service_name="summary", input_key="demo", tech_results=[])
        """
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

        result = ServiceResult(
            service_name=self.service_name,
            input_key=repr(tech_input),
            tech_results=list(
                await asyncio.gather(*(self._run_technology(t, tech_input) for t in techs))
            ),
        )
        return await self.execute_service(data, result)

    async def _run_technology(self, tech: object, tech_input: object) -> TechResult:
        """Run one adapter without letting its failure cancel sibling technologies.

        Services turn platform items into adapter requests and normalize results so stages handle
        success, skip, and failure the same way.

        Args:
            tech: Technology adapter exposing a stable name and execute method.
            tech_input: Payload after service-specific shaping, ready for the adapter.

        Returns:
            TechResult containing adapter input, output, success state, and error text if any.

        Examples:
            Input:
                await _run_technology(
                    tech=summary_adapter,
                    tech_input={"video_id": "abc123"},
                )
            Output:
                TechResult(tech_name="youtube", input={"video_id": "abc123"}, output={"comments_status": "available"}, success=True)
        """
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

    def _technology_input(self, data: TInput) -> object:
        """Shape the service payload before it is sent to a technology adapter.

        Services translate platform data into adapter calls and normalize the result so stages can
        handle success, skip, and failure consistently.

        Args:
            data: Input payload at this service, technology, or pipeline boundary.

        Returns:
            Normalized value needed by the next operation.

        Examples:
            Input:
                _technology_input(
                    data={"title": "Example", "url": "https://youtu.be/demo"},
                )
            Output:
                "AI safety"
        """
        return data

    @abstractmethod
    def _get_technologies(self) -> list[object]:
        """Return technology instances to run for one input.

        Services translate platform data into adapter calls and normalize the result so stages can
        handle success, skip, and failure consistently.

        Returns:
            List in the order expected by the next stage, renderer, or CLI formatter.

        Examples:
            Input:
                _get_technologies()
            Output:
                [{"title": "Example", "url": "https://youtu.be/demo"}]
        """
