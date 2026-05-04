"""Command: show-pending. Display staged suggestion entries."""

from __future__ import annotations

import argparse

from social_research_probe.utils.core.exit_codes import ExitCode


def run(args: argparse.Namespace) -> int:
    """Execute the `show pending` CLI command.

    Command helpers keep user-facing parsing, validation, and output formatting out of pipeline and
    service code.

    Args:
        args: Parsed argparse namespace for the command being dispatched.

    Returns:
        Integer count, limit, status code, or timeout used by the caller.

    Examples:
        Input:
            run(
                args=argparse.Namespace(output="json"),
            )
        Output:
            5
    """
    from social_research_probe.commands import load_pending
    from social_research_probe.utils.display.cli_output import emit

    emit(load_pending(), args.output)
    return ExitCode.SUCCESS
