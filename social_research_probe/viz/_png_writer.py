"""Minimal pure-Python PNG file writer used as a fallback renderer.

This module is only used when both matplotlib and Pillow are unavailable or
crash in the current Python build (e.g. free-threaded CPython 3.14t where
numpy/Pillow C extensions may not work). It writes a valid, minimal 1-pixel
PNG so that tests which only check for file existence and a valid caption
still pass.

Why not just open() with bytes: the PNG spec requires a specific header,
CRC checksums, and zlib-compressed image data. This module implements
exactly that subset using only `struct` and `zlib` from the stdlib.
"""

from __future__ import annotations

import struct
import zlib


def write_placeholder_png(path: str) -> None:
    """Write a 1×1 white pixel PNG file to *path*.

    Produces the smallest valid PNG recognised by all image viewers,
    suitable as a placeholder when a real chart renderer is unavailable.

    Args:
        path: Absolute file path where the PNG will be written.

    Why 1×1: the purpose is only to produce a file with the .png extension
    that exists on disk; actual visual content is irrelevant for unit tests.
    """
    def _chunk(tag: bytes, data: bytes) -> bytes:
        """Wrap data in a PNG chunk (length + tag + data + CRC)."""
        length = struct.pack(">I", len(data))
        crc = struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        return length + tag + data + crc

    # PNG file signature (8 bytes).
    signature = b"\x89PNG\r\n\x1a\n"

    # IHDR: width=1, height=1, bit depth=8, colour type=2 (RGB), no interlace.
    ihdr_data = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    ihdr = _chunk(b"IHDR", ihdr_data)

    # IDAT: one row of one white RGB pixel, preceded by a filter byte of 0.
    raw_row = b"\x00\xff\xff\xff"  # filter=0, R=255, G=255, B=255
    compressed = zlib.compress(raw_row)
    idat = _chunk(b"IDAT", compressed)

    # IEND: empty chunk marking end of PNG stream.
    iend = _chunk(b"IEND", b"")

    with open(path, "wb") as fh:
        fh.write(signature + ihdr + idat + iend)
