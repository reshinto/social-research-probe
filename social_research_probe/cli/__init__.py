"""Command-line interface entry point.

Provides an argparse-based shell that parses CLI input and dispatches
execution to subcommand handlers.
"""

from __future__ import annotations

import argparse
import os
import sys

from social_research_probe.config import resolve_data_dir
from social_research_probe.utils.core.errors import SrpError

from .handlers import handlers_factory
from .parsers import _global_parser
from .utils import _emit as _emit
from .utils import _id_selector as _id_selector
from .utils import _to_markdown as _to_markdown
from .utils import _to_text as _to_text


def _dispatch(args: argparse.Namespace) -> int:
    """Dispatch parsed CLI arguments to the appropriate handler.

    Args:
        args: Parsed CLI arguments.

    Returns:
        Exit code from the selected handler.
    """
    # Override the data directory used for config, cache, and output.
    # Defaults to .skill-data/ in the current directory, or ~/.social-research-probe/
    data_dir = resolve_data_dir(args.data_dir)
    os.environ["SRP_DATA_DIR"] = str(data_dir)

    handler = handlers_factory().get(args.command)
    if handler is None:
        return 2
    return handler(args, data_dir)


def main(argv: list[str] | None = None) -> int:
    """Run the command-line interface.

    Parses arguments and dispatches execution to subcommand handlers.

    Example:
        srp research youtube

    Args:
        argv: Optional argument list. Defaults to sys.argv.

    Returns:
        Exit status code.

    Raises:
        SrpError: Raised by handlers and converted to exit codes.
    """
    import social_research_probe as _srp_pkg

    parser = _global_parser()
    args = parser.parse_args(argv)
    if getattr(args, "version", False):
        print(f"srp {_srp_pkg.get_version()}  ({_srp_pkg.__file__})")
        return 0
    if args.command is None:
        parser.print_help(sys.stderr)
        return 2
    try:
        return _dispatch(args)
    except SrpError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return exc.exit_code


if __name__ == "__main__":
    sys.exit(main())
