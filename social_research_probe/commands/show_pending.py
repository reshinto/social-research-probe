"""Command: show-pending. Display staged suggestion entries."""

from __future__ import annotations

import argparse

from social_research_probe.utils.core.exit_codes import ExitCode


def run(args: argparse.Namespace) -> int:
    from social_research_probe.commands import load_pending
    from social_research_probe.utils.display.cli_output import emit

    emit(load_pending(), args.output)
    return ExitCode.SUCCESS
