"""Command: update-topics. Add, remove, or rename topics."""

from __future__ import annotations

import argparse

from social_research_probe.utils.core.exit_codes import ExitCode


def run(args: argparse.Namespace) -> int:
    from social_research_probe.commands import add_topics, remove_topics, rename_topic
    from social_research_probe.utils.display.cli_output import emit

    if args.add:
        add_topics(args.add, force=args.force)
    elif args.remove:
        remove_topics(args.remove)
    else:
        old, new = args.rename
        rename_topic(old, new)
    emit({"ok": True}, args.output)
    return ExitCode.SUCCESS
