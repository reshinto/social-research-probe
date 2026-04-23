"""commands/render.py — CLI command to render charts and stats for a research packet.

Takes a research packet (produced by run-research) and generates:
  - Statistical summaries of the top-N items' scores.
  - Chart images saved as PNG files.
  - A text report with section captions.

This lets users inspect research results offline, outside of the AI skill flow.

Called by: cli._dispatch when args.command == 'render'.
"""

from __future__ import annotations

import json
import sys

from social_research_probe.packet import unwrap_packet
from social_research_probe.technologies.charts.selector import select_and_render
from social_research_probe.technologies.statistics.selector import select_and_run


def run(packet_path: str, output_dir: str | None = None) -> int:
    """Read a packet JSON file and render stats + charts for the top-N items.

    Loads the packet, extracts the "overall" score from each top-N item,
    passes those scores to the stats and viz selectors, then prints a JSON
    report with stat names/values/captions and chart path/caption to stdout.

    Args:
        packet_path: Path to the JSON packet file produced by run-research.
        output_dir: Directory to save chart image files. If None, the viz
            selector uses a system temp directory.

    Returns:
        Exit code (0 on success).

    Raises:
        ValidationError: If packet_path does not exist, cannot be opened, or
            is not valid JSON.
    """
    from social_research_probe.errors import ValidationError

    try:
        with open(packet_path) as f:
            payload = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        raise ValidationError(f"cannot read packet file: {exc}") from exc
    packet = unwrap_packet(payload)
    if not isinstance(packet, dict):
        raise ValidationError("packet file must contain a JSON object")

    items = packet.get("items_top_n", [])
    # Extract the "overall" composite score from each item's scores dict.
    # Items that lack the key default to 0.0 so the lists stay aligned.
    overall_scores = [it.get("scores", {}).get("overall", 0.0) for it in items]

    stat_results = select_and_run(overall_scores, label="overall_score")
    chart = select_and_render(overall_scores, label="overall_score", output_dir=output_dir)

    report = {
        "stats": [{"name": r.name, "value": r.value, "caption": r.caption} for r in stat_results],
        "chart": {"path": chart.path, "caption": chart.caption},
    }
    sys.stdout.write(json.dumps(report, indent=2) + "\n")
    return 0
