"""Claim extraction service: enriches items with deterministic extracted claims."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.services import BaseService, ServiceResult, TechResult
from social_research_probe.utils.claims.types import ExtractedClaim


def _claims_from_result(result: ServiceResult) -> list[ExtractedClaim]:
    for tr in result.tech_results:
        if tr.success and isinstance(tr.output, list):
            return tr.output
    return []


def _with_output(tr: TechResult, output: object) -> TechResult:
    return TechResult(tech_name=tr.tech_name, input=tr.input, output=output, success=tr.success)


class ClaimExtractionService(BaseService):
    """Extract structured claims from item text and merge them into the item dict."""

    service_name: ClassVar[str] = "youtube.enriching.claims"
    enabled_config_key: ClassVar[str] = "services.youtube.enriching.claims"

    def _get_technologies(self) -> list[object]:
        from social_research_probe.technologies.claims import ClaimExtractionTech

        return [ClaimExtractionTech()]

    async def execute_service(self, data: object, result: ServiceResult) -> ServiceResult:
        if not isinstance(data, dict):
            return result
        claims = _claims_from_result(result)
        merged = {**data, "extracted_claims": claims}
        if result.tech_results:
            result.tech_results[0] = _with_output(result.tech_results[0], merged)
        return result
