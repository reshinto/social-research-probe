"""Claim extraction service: enriches items with deterministic extracted claims."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.services import BaseService, ServiceResult, TechResult
from social_research_probe.utils.claims.types import ExtractedClaim


def _claims_from_result(result: ServiceResult) -> list[ExtractedClaim]:
    """Extract normalized claims from a successful claim-extraction service result.

    Extraction, review, corroboration, and reporting all need the same claim shape.

    Args:
        result: Service or technology result being inspected for payload and diagnostics.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            _claims_from_result(
                result=ServiceResult(service_name="comments", input_key="demo", tech_results=[]),
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
    """
    for tr in result.tech_results:
        if tr.success and isinstance(tr.output, list):
            return tr.output
    return []


def _with_output(tr: TechResult, output: object) -> TechResult:
    """Return a TechResult copy with a replacement output payload.

    Services translate platform data into adapter calls and normalize the result so stages can
    handle success, skip, and failure consistently.

    Args:
        tr: Technology result object carrying adapter output and success diagnostics.
        output: Adapter or helper output being wrapped into the project result shape.

    Returns:
        TechResult containing adapter input, output, success state, and error text if any.

    Examples:
        Input:
            _with_output(
                tr=TechResult(tech_name="youtube", input={"video_id": "abc123"}, output={"comments_status": "available"}, success=True),
                output={"comments_status": "available"},
            )
        Output:
            TechResult(tech_name="youtube", input={"video_id": "abc123"}, output={"comments_status": "available"}, success=True)
    """
    return TechResult(tech_name=tr.tech_name, input=tr.input, output=output, success=tr.success)


class ClaimExtractionService(BaseService):
    """Extract structured claims from item text and merge them into the item dict.

    Examples:
        Input:
            ClaimExtractionService
        Output:
            ClaimExtractionService
    """

    service_name: ClassVar[str] = "youtube.enriching.claims"
    enabled_config_key: ClassVar[str] = "services.youtube.enriching.claims"

    def _get_technologies(self) -> list[object]:
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
        from social_research_probe.technologies.claims import ClaimExtractionTech

        return [ClaimExtractionTech()]

    async def execute_service(self, data: object, result: ServiceResult) -> ServiceResult:
        """Convert adapter output into the claim extraction service result.

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
        if not isinstance(data, dict):
            return result
        claims = _claims_from_result(result)
        merged = {**data, "extracted_claims": claims}
        if result.tech_results:
            result.tech_results[0] = _with_output(result.tech_results[0], merged)
        return result
