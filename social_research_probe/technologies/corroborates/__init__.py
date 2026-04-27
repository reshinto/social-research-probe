"""Corroboration technology adapters."""



from __future__ import annotations
from typing import ClassVar
from social_research_probe.technologies import BaseTechnology
class CorroborationHostTech(BaseTechnology[object, dict]):
    """Technology wrapper for corroborating a single item's claim."""
    name: ClassVar[str] = "corroboration_host"
    def __init__(self, providers: list[str]):
        super().__init__()
        self.providers = providers
    async def _execute(self, input_data: object) -> dict:
        from social_research_probe.services.corroborating import corroborate_claim
        from social_research_probe.technologies.validation.claim_extractor import Claim
        title = input_data.get("title", "") if isinstance(input_data, dict) else str(input_data)
        url = input_data.get("url") if isinstance(input_data, dict) else None
        claim = Claim(text=title, source_text=title, index=0, source_url=url)
        return await corroborate_claim(claim, self.providers)
