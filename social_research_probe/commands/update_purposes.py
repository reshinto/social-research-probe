"""Command: update-purposes. Add, remove, or rename purposes."""

from __future__ import annotations

import argparse

from social_research_probe.utils.core.exit_codes import ExitCode


def run(args: argparse.Namespace) -> int:
    """Build the small payload that carries ok through this workflow.

    This is the command boundary: argparse passes raw options in, and the rest of the application
    receives validated project data or a clear error.

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
    from social_research_probe.cli.dsl import parse_name_method, parse_topic_values
    from social_research_probe.commands import add_purpose, remove_purposes, rename_purpose
    from social_research_probe.utils.display.cli_output import emit

    if args.add:
        name, method = parse_name_method(args.add)
        add_purpose(name=name, method=method, force=args.force)
    elif args.remove:
        remove_purposes(parse_topic_values(args.remove))
    else:
        old, new = args.rename
        rename_purpose(old, new)
    emit({"ok": True}, args.output)
    return ExitCode.SUCCESS
