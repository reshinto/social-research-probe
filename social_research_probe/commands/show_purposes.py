"""Command: show-purposes. Print the current purposes registry."""

from __future__ import annotations

import argparse
from pathlib import Path


def run(args: argparse.Namespace, data_dir: Path) -> int:
    from social_research_probe.utils.display.cli_output import _emit
    from social_research_probe.utils.command_models.purposes import show_purposes

    _emit({"purposes": show_purposes(data_dir)}, args.output)
    return 0
