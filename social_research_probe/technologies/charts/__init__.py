"""Chart rendering technology adapters."""

from __future__ import annotations

import asyncio
import struct
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from social_research_probe.technologies import BaseTechnology


@dataclass
class ChartResult:
    """The output of a chart-rendering function.

    Keeping these fields together makes pipeline handoffs easier to inspect and harder to
    accidentally reorder.

    Examples:
        Input:
            ChartResult
        Output:
            ChartResult(path="charts/engagement.png", caption="Engagement trend")
    """

    path: str
    caption: str


def write_placeholder_png(path: str) -> None:
    """Write a 1x1 white pixel PNG to *path* when a real renderer is unavailable.

    Chart code normalizes report data before rendering, which keeps presentation details out of
    analysis and service code.

    Args:
        path: Filesystem location used to read, write, or resolve project data.

    Returns:
        None. The result is communicated through state mutation, file/database writes, output, or an
        exception.

    Examples:
        Input:
            write_placeholder_png(
                path=Path("report.html"),
            )
        Output:
            None
    """

    def _chunk(tag: bytes, data: bytes) -> bytes:
        """Build one PNG chunk with length and checksum bytes.

        Chart code normalizes report data before rendering, which keeps presentation details out of
        analysis and service code.

        Args:
            tag: Four-byte PNG chunk tag.
            data: Input payload at this service, technology, or pipeline boundary.

        Returns:
            Bytes in the binary format expected by the caller.

        Examples:
            Input:
                _chunk(
                    tag=b"IHDR",
                    data={"title": "Example", "url": "https://youtu.be/demo"},
                )
            Output:
                b"PNG chunk bytes"
        """
        length = struct.pack(">I", len(data))
        crc = struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        return length + tag + data + crc

    signature = b"\x89PNG\r\n\x1a\n"
    ihdr = _chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
    idat = _chunk(b"IDAT", zlib.compress(b"\x00\xff\xff\xff"))
    iend = _chunk(b"IEND", b"")

    with open(path, "wb") as fh:
        fh.write(signature + ihdr + idat + iend)


def items_from(data: object) -> list[dict]:
    """Extract scored_items list from input data dict.

    Chart code normalizes report data before rendering, which keeps presentation details out of
    analysis and service code.

    Args:
        data: Input payload at this service, technology, or pipeline boundary.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            items_from(
                data={"title": "Example", "url": "https://youtu.be/demo"},
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
    """
    if not isinstance(data, dict):
        return []
    return [d for d in data.get("scored_items", []) if isinstance(d, dict)]


def ensure_charts_dir() -> Path:
    """Load config and create/return the charts output directory.

    Chart code normalizes report data before rendering, which keeps presentation details out of
    analysis and service code.

    Returns:
        Resolved filesystem path, or None when the optional path is intentionally absent.

    Examples:
        Input:
            ensure_charts_dir()
        Output:
            Path("report.html")
    """
    from social_research_probe.config import load_active_config

    path = load_active_config().data_dir / "charts"
    path.mkdir(parents=True, exist_ok=True)
    return path


async def render_charts(items: list[dict], charts_dir: Path) -> list:
    """Render charts for *items* into *charts_dir*.

    Chart code normalizes report data before rendering, which keeps presentation details out of
    analysis and service code.

    Args:
        items: Ordered source items being carried through the current pipeline step.
        charts_dir: Filesystem location used to read, write, or resolve project data.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            await render_charts(
                items=[{"title": "Example", "url": "https://youtu.be/demo"}],
                charts_dir=Path(".skill-data"),
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
    """
    from social_research_probe.technologies.charts.render import render_all

    if not items:
        return []
    return await asyncio.to_thread(render_all, items, charts_dir)


class ChartsTech(BaseTechnology[object, list]):
    """Technology wrapper for generating the full chart suite.

    Examples:
        Input:
            ChartsTech
        Output:
            ChartsTech
    """

    name: ClassVar[str] = "charts_suite"
    enabled_config_key: ClassVar[str] = "charts_suite"

    async def _execute(self, input_data: object) -> list:
        """Run this component and return the project-shaped output expected by its service.

        Chart code normalizes report data before rendering, which keeps presentation details out of
        analysis and service code.

        Args:
            input_data: Input payload at this service, technology, or pipeline boundary.

        Returns:
            List in the order expected by the next stage, renderer, or CLI formatter.

        Examples:
            Input:
                await _execute(
                    input_data={"title": "Example", "url": "https://youtu.be/demo"},
                )
            Output:
                [{"title": "Example", "url": "https://youtu.be/demo"}]
        """
        chart_items = items_from(input_data)
        out_dir = ensure_charts_dir()
        return await render_charts(chart_items, out_dir)
