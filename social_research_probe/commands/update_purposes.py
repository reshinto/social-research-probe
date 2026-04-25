"""Command: update-purposes. Add, remove, or rename purposes."""

from __future__ import annotations

import argparse

from social_research_probe.utils.core.exit_codes import ExitCode


def run(args: argparse.Namespace) -> int:
    from social_research_probe.commands import add_purpose, remove_purposes, rename_purpose
    from social_research_probe.utils.core.errors import ValidationError
    from social_research_probe.utils.display.cli_output import emit

    if args.add:
        if len(args.add) != 2:
            raise ValidationError("--add requires exactly: NAME METHOD")
        name, method = args.add
        add_purpose(name=name, method=method, force=args.force)
    elif args.remove:
        remove_purposes(args.remove)
    else:
        old, new = args.rename
        rename_purpose(old, new)
    emit({"ok": True}, args.output)
    return ExitCode.SUCCESS
