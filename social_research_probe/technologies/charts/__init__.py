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
    """The output of a chart-rendering function."""

    path: str
    caption: str


def write_placeholder_png(path: str) -> None:
    """Write a 1x1 white pixel PNG to *path* when a real renderer is unavailable."""

    def _chunk(tag: bytes, data: bytes) -> bytes:
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
    """Extract scored_items list from input data dict."""
    if not isinstance(data, dict):
        return []
    return [d for d in data.get("scored_items", []) if isinstance(d, dict)]


def ensure_charts_dir() -> Path:
    """Load config and create/return the charts output directory."""
    from social_research_probe.config import load_active_config

    path = load_active_config().data_dir / "charts"
    path.mkdir(parents=True, exist_ok=True)
    return path


async def render_charts(items: list[dict], charts_dir: Path) -> list:
    """Render charts for *items* into *charts_dir*."""
    from social_research_probe.technologies.charts.render import render_all

    if not items:
        return []
    return await asyncio.to_thread(render_all, items, charts_dir)


class ChartsTech(BaseTechnology[object, list]):
    """Technology wrapper for generating the full chart suite."""

    name: ClassVar[str] = "charts_suite"
    enabled_config_key: ClassVar[str] = "charts_suite"

    async def _execute(self, input_data: object) -> list:
        chart_items = items_from(input_data)
        out_dir = ensure_charts_dir()
        return await render_charts(chart_items, out_dir)
