"""Synthesis technology adapters."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.technologies import BaseTechnology


class SynthesisTech(BaseTechnology[object, str]):
    """Technology for generating the final research synthesis."""

    name: ClassVar[str] = "llm_synthesis"

    async def _execute(self, input_data: object) -> str | None:
        from social_research_probe.utils.llm.ensemble import multi_llm_prompt
        from social_research_probe.technologies.synthesizing.llm_contract import (
            build_synthesis_prompt,
        )

        prompt = build_synthesis_prompt(input_data if isinstance(input_data, dict) else {})
        synthesis = await multi_llm_prompt(prompt) or ""
        return synthesis if synthesis else None
