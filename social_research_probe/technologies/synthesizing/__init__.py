"""Synthesis technology adapters."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.technologies import BaseTechnology


class SynthesisTech(BaseTechnology[object, str]):
    """Technology for generating the final research synthesis.

    Examples:
        Input:
            SynthesisTech
        Output:
            SynthesisTech
    """

    name: ClassVar[str] = "llm_synthesis"
    enabled_config_key: ClassVar[str] = "llm_synthesis"

    async def _execute(self, input_data: object) -> str | None:
        """Run this component and return the project-shaped output expected by its service.

        The helper keeps a small project rule named and documented at the boundary where it is used.

        Args:
            input_data: Input payload at this service, technology, or pipeline boundary.

        Returns:
            Normalized value needed by the next operation.

        Examples:
            Input:
                await _execute(
                    input_data={"title": "Example", "url": "https://youtu.be/demo"},
                )
            Output:
                "AI safety"
        """
        from social_research_probe.technologies.synthesizing.llm_contract import (
            build_synthesis_prompt,
        )
        from social_research_probe.utils.llm.ensemble import multi_llm_prompt

        prompt = build_synthesis_prompt(input_data if isinstance(input_data, dict) else {})
        synthesis = await multi_llm_prompt(prompt) or ""
        return synthesis if synthesis else None
