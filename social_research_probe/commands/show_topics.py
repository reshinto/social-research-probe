"""Command: show-topics. Print the current topics list."""

from __future__ import annotations

import argparse
from pathlib import Path
from social_research_probe.utils.core.exit_codes import ExitCode


def run(args: argparse.Namespace) -> int:
    from social_research_probe.commands import show_topics
    from social_research_probe.utils.display.cli_output import emit

    emit({"topics": show_topics(data_dir)}, args.output)
    return ExitCode.SUCCESS
