"""Command: show-pending. Display staged suggestion entries."""

from __future__ import annotations

import argparse
from pathlib import Path


def run(args: argparse.Namespace, data_dir: Path) -> int:
    from social_research_probe.utils.command_models.suggestions import show_pending
    from social_research_probe.utils.display.cli_output import _emit

    _emit(show_pending(data_dir), args.output)
    return 0
