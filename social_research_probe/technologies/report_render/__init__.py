"""Report rendering technology adapters."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.technologies import BaseTechnology


class HtmlRenderTech(BaseTechnology[object, str]):
    """Technology for generating the final HTML report."""

    name: ClassVar[str] = "html_render"
    enabled_config_key: ClassVar[str] = "html_render"

    async def _execute(self, input_data: object) -> str:
        import asyncio

        from social_research_probe.technologies.report_render.html.raw_html.youtube import (
            write_html_report,
        )

        report = input_data.get("report") if isinstance(input_data, dict) else input_data
        return await asyncio.to_thread(write_html_report, report)
