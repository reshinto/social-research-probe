"""commands/report.py — Re-render an HTML report from a saved packet file.

Intended as the override path when an operator wants to replace sections
10-11 (compiled synthesis and opportunity analysis) after research has
already emitted the packet JSON.

Usage:
    srp report --packet PATH [--synthesis-10 FILE] [--synthesis-11 FILE] [--out PATH]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from social_research_probe.errors import ValidationError
from social_research_probe.packet import unwrap_packet


def run(
    packet_path: str,
    synthesis_10_path: str | None,
    synthesis_11_path: str | None,
    out_path: str | None,
) -> int:
    """Read a packet JSON file and write (or rewrite) its HTML report.

    Args:
        packet_path: Path to the packet JSON file.
        synthesis_10_path: Optional path to a file containing compiled synthesis text.
        synthesis_11_path: Optional path to a file containing opportunity analysis text.
        out_path: Destination HTML path. If None, prints to stdout.

    Returns:
        Exit code (0 on success).

    Raises:
        ValidationError: If the packet file cannot be read or is invalid JSON.
    """
    try:
        payload = json.loads(Path(packet_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot read packet file: {exc}") from exc
    packet = unwrap_packet(payload)
    if not isinstance(packet, dict):
        raise ValidationError("packet file must contain a JSON object")

    synthesis_10 = _read_text_file(synthesis_10_path)
    synthesis_11 = _read_text_file(synthesis_11_path)

    from social_research_probe.render.html import render_html

    # Resolve charts_dir relative to the packet file's parent directory if
    # the standard layout is present (packet file next to a charts/ sibling).
    packet_parent = Path(packet_path).parent
    charts_dir = packet_parent / "charts"
    charts_dir_arg = charts_dir if charts_dir.is_dir() else None

    rendered_packet = dict(packet)
    if synthesis_10 is not None:
        rendered_packet["compiled_synthesis"] = synthesis_10
    if synthesis_11 is not None:
        rendered_packet["opportunity_analysis"] = synthesis_11

    html_content = render_html(rendered_packet, charts_dir=charts_dir_arg)

    if out_path:
        dest = Path(out_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(html_content, encoding="utf-8")
        print(f"[srp] HTML report written: {dest.resolve().as_uri()}", file=sys.stderr)
    else:
        sys.stdout.write(html_content)
    return 0


def _read_text_file(path: str | None) -> str | None:
    """Read a text file's content or return None if path is None."""
    if path is None:
        return None
    try:
        return Path(path).read_text(encoding="utf-8").strip() or None
    except OSError as exc:
        raise ValidationError(f"cannot read file {path!r}: {exc}") from exc
