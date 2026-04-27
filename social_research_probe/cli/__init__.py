"""Command-line entry point for the Social Research Probe CLI.

This module owns the top-level CLI execution flow for the ``srp`` command. It
builds the root parser, parses user-provided arguments, handles global commands
such as ``--version``, resolves runtime configuration paths, and dispatches
validated arguments to the appropriate subcommand handler.

The goal is to keep process-level concerns here while leaving parser definition
and command-specific behavior to dedicated modules.
"""

from __future__ import annotations

import argparse
import sys

from social_research_probe.config import resolve_data_dir
from social_research_probe.utils.cli import _id_selector as _id_selector
from social_research_probe.utils.core.errors import SrpError

from .handlers import handlers_factory
from .parsers import global_parser

EXIT_SUCCESS = 0
EXIT_INVALID_USAGE = 2


def _handle_version(args: argparse.Namespace) -> bool:
    """Print package version information when requested.

    Args:
        args: Parsed CLI arguments that may include the version flag.

    Returns:
        ``True`` if version information was printed and normal command
        execution should stop; otherwise ``False``.

    """
    import social_research_probe as _srp_pkg
    from social_research_probe.commands import SpecialCommand

    if getattr(args, SpecialCommand.VERSION, False):
        print(f"srp {_srp_pkg.get_version()}  ({_srp_pkg.__file__})")
        return True
    return False


def _dispatch(args: argparse.Namespace) -> int:
    """Route parsed arguments to the selected command handler.

    This function prepares shared runtime state, such as the resolved data
    directory, then looks up and invokes the handler for ``args.command``.

    Args:
        args: Parsed CLI arguments containing the selected command and any
            command-specific options.

    Returns:
        Process exit code returned by the selected handler, or
        ``EXIT_INVALID_USAGE`` when no matching handler exists.
    """
    resolve_data_dir(args.data_dir)
    handler = handlers_factory().get(args.command)
    if handler is None:
        return EXIT_INVALID_USAGE
    return handler(args)


def main(argv: list[str] | None = None) -> int:
    """Run the Social Research Probe command-line interface.

    Builds the parser, parses command-line input, handles global flags, validates
    that a command was selected, and dispatches execution to the matching
    subcommand handler. Application-level errors are rendered to stderr and
    converted into process exit codes.

    Args:
        argv: Optional argument list to parse. When omitted, argparse reads from
            ``sys.argv``.

    Returns:
        Process exit code suitable for ``sys.exit``.

    Raises:
        SrpError: Handled internally when raised by command handlers.
    """
    from social_research_probe.services.corroborating import (
        ensure_providers_registered,
    )
    from social_research_probe.services.llm.core.helpers.registry import ensure_runners_registered

    ensure_runners_registered()
    ensure_providers_registered()
    parser = global_parser()
    args = parser.parse_args(argv)
    if _handle_version(args):
        return EXIT_SUCCESS
    if args.command is None:
        parser.print_help(sys.stderr)
        return EXIT_INVALID_USAGE
    try:
        return _dispatch(args)
    except SrpError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return exc.exit_code


if __name__ == "__main__":
    sys.exit(main())
