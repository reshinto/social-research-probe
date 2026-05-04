"""Report rendering technology adapters."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.technologies import BaseTechnology


class HtmlRenderTech(BaseTechnology[object, str]):
    """Technology for generating the final HTML report.

    Examples:
        Input:
            HtmlRenderTech
        Output:
            HtmlRenderTech
    """

    name: ClassVar[str] = "html_render"
    enabled_config_key: ClassVar[str] = "html_render"

    async def _execute(self, input_data: object) -> str:
        """Run this component and return the project-shaped output expected by its service.

        Report rendering has to turn loose research dictionaries into deterministic files, so each
        formatting rule is isolated and easy to review.

        Args:
            input_data: Input payload at this service, technology, or pipeline boundary.

        Returns:
            Normalized string used as a config key, provider value, or report field.

        Examples:
            Input:
                await _execute(
                    input_data={"title": "Example", "url": "https://youtu.be/demo"},
                )
            Output:
                "AI safety"
        """
        import asyncio

        from social_research_probe.technologies.report_render.html.raw_html.youtube import (
            write_html_report,
        )

        report = input_data.get("report") if isinstance(input_data, dict) else input_data
        return await asyncio.to_thread(write_html_report, report)
