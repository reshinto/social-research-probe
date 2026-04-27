"""Chart rendering technology adapters."""

from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass
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


class ChartsTech(BaseTechnology[object, list]):
    """Technology wrapper for generating the full chart suite."""

    name: ClassVar[str] = "charts_suite"

    async def _execute(self, input_data: object) -> list:
        from social_research_probe.services.analyzing.charts import ChartsService

        items = ChartsService._items_from(input_data)
        out_dir = ChartsService._ensure_charts_dir()
        return await ChartsService._render_with_cache(items, out_dir)
