"""LLM service: structured JSON LLM calls via registered runners with fallback."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.services import BaseService, ServiceResult, TechResult
from social_research_probe.technologies.llms import LLMTech
from social_research_probe.utils.core.types import RunnerName


class LLMService(BaseService[str, dict]):
    """Structured LLM service: tries runners in priority order until one succeeds.

    Examples:
        Input:
            LLMService
        Output:
            LLMService
    """

    service_name: ClassVar[str] = "llm"
    enabled_config_key: ClassVar[str] = "llm"
    run_technologies_concurrently: ClassVar[bool] = False

    def __init__(self, preferred: RunnerName, schema: dict | None = None) -> None:
        """Store constructor options used by later method calls.

        Services turn platform items into adapter requests and normalize results so stages handle
        success, skip, and failure the same way.

        Args:
            preferred: Provider or runner selected for this operation.
            schema: JSON schema that the LLM or validator must satisfy.

        Returns:
            None. The result is communicated through state mutation, file/database writes, output, or an
            exception.

        Examples:
            Input:
                __init__(
                    preferred="codex",
                    schema={"enabled": True},
                )
            Output:
                None
        """
        self._preferred = preferred
        self._schema = schema

    def _get_technologies(self) -> list[LLMTech]:
        """Return the technology adapters this service is allowed to run.

        Services turn platform items into adapter requests and normalize results so stages handle
        success, skip, and failure the same way.

        Returns:
            List in the order expected by the next stage, renderer, or CLI formatter.

        Examples:
            Input:
                _get_technologies()
            Output:
                [{"title": "Example", "url": "https://youtu.be/demo"}]
        """
        from social_research_probe.utils.llm.registry import list_runners

        names = [self._preferred, *[n for n in list_runners() if n != self._preferred]]
        return [LLMTech(n, self._schema) for n in names]

    async def execute_service(self, data: str, result: ServiceResult) -> ServiceResult:
        """Convert adapter output into the llmservice service result.

        The caller gets one stable method even when this component needs fallbacks or provider-specific
        handling.

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
        tech_results: list[TechResult] = result.tech_results
        if not tech_results:
            for tech in self._get_technologies():
                tech.caller_service = self.service_name
                try:
                    output = await tech.execute(data)
                    tr = TechResult(
                        tech_name=tech.name,
                        input=data,
                        output=output,
                        success=output is not None,
                    )
                    tech_results.append(tr)
                    if tr.success:
                        break
                except Exception as exc:
                    tech_results.append(
                        TechResult(
                            tech_name=tech.name,
                            input=data,
                            output=None,
                            success=False,
                            error=str(exc),
                        )
                    )

        return ServiceResult(
            service_name=self.service_name,
            input_key=repr(data),
            tech_results=tech_results,
        )
