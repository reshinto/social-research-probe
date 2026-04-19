"""commands/research.py — CLI wrapper for the run-research pipeline.

This module provides a thin interface between the CLI argument namespace
and the pipeline.run_research() function. It is NOT used in skill mode —
skill mode calls pipeline.run_research directly and exits via llm/host.py.

Called by: cli._dispatch when args.command == 'run-research' and mode == 'cli'.
"""

from __future__ import annotations

import sys
from pathlib import Path

from social_research_probe.commands.parse import parse as parse_dsl
from social_research_probe.pipeline import run_research
from social_research_probe.synthesize.formatter import render_full


def run(platform: str, dsl_args: list[str], data_dir: Path, mode: str = "cli") -> int:
    """Parse DSL arguments and execute the research pipeline.

    Builds a canonical DSL string from the platform and positional dsl_args,
    parses it, then hands off to pipeline.run_research. In cli mode the
    resulting packet is printed as indented JSON to stdout. In skill mode the
    pipeline itself is responsible for emitting output and typically exits
    directly, so this function simply calls through and returns 0.

    Args:
        platform: The platform adapter name (e.g. 'youtube').
        dsl_args: Raw DSL strings from argparse (e.g. ['"ai"->latest-news']).
        data_dir: Path to the user's data directory.
        mode: 'cli' (prints result) or 'skill' (emits packet and exits).

    Returns:
        Exit code (0 on success).
    """
    # Reconstruct the full DSL string the parser expects, e.g.:
    # "run-research platform:youtube "ai"->latest-news"
    raw = f"run-research platform:{platform} " + " ".join(dsl_args)
    cmd = parse_dsl(raw)
    packet = run_research(cmd, data_dir, mode)
    if mode == "cli":
        sys.stdout.write(render_full(packet))
    return 0
