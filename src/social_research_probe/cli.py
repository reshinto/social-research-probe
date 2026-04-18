"""CLI entry point. Subcommands are registered here and dispatched by name."""
from __future__ import annotations

import argparse
import sys
from collections.abc import Callable

from social_research_probe.errors import SrpError

# Registry populated by subcommand modules in later tasks.
_SUBCOMMANDS: dict[str, tuple[Callable[[argparse.ArgumentParser], None], Callable[[argparse.Namespace], int]]] = {}


def register_subcommand(
    name: str,
    configure: Callable[[argparse.ArgumentParser], None],
    handler: Callable[[argparse.Namespace], int],
) -> None:
    _SUBCOMMANDS[name] = (configure, handler)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="srp", description="Evidence-first social-media research.")
    parser.add_argument("--mode", choices=["skill", "cli"], default="cli")
    parser.add_argument("--output", choices=["text", "json", "markdown"], default="text")
    parser.add_argument("--data-dir", default=None)
    parser.add_argument("--verbose", action="store_true")

    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")
    for name, (configure, _handler) in _SUBCOMMANDS.items():
        sub = subparsers.add_parser(name)
        configure(sub)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help(sys.stderr)
        return 2

    _configure, handler = _SUBCOMMANDS[args.command]
    try:
        return handler(args)
    except SrpError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return exc.exit_code


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
