"""Command: show-purposes. Print the current purposes registry."""

from __future__ import annotations

import argparse
from pathlib import Path
from social_research_probe.utils.core.exit_codes import ExitCode


def run(args: argparse.Namespace) -> int:
    from social_research_probe.commands import show_purposes
    from social_research_probe.utils.display.cli_output import emit

    emit({"purposes": show_purposes(data_dir)}, args.output)
    return ExitCode.SUCCESS
