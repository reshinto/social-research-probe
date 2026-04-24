"""Command: show-topics. Print the current topics list."""

from __future__ import annotations

import argparse
from pathlib import Path


def run(args: argparse.Namespace, data_dir: Path) -> int:
    from social_research_probe.utils.display.cli_output import _emit
    from social_research_probe.utils.command_models.topics import show_topics

    _emit({"topics": show_topics(data_dir)}, args.output)
    return 0
