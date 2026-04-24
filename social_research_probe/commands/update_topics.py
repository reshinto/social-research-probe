"""Command: update-topics. Add, remove, or rename topics."""

from __future__ import annotations

import argparse
from pathlib import Path


def run(args: argparse.Namespace, data_dir: Path) -> int:
    from social_research_probe.cli.dsl_parser import _parse_quoted_list, _take_quoted
    from social_research_probe.cli.utils import _emit
    from social_research_probe.utils.command_models.topics import (
        add_topics,
        remove_topics,
        rename_topic,
    )
    from social_research_probe.utils.core.errors import ValidationError

    if args.add:
        add_topics(data_dir, _parse_quoted_list(args.add), force=args.force)
    elif args.remove:
        remove_topics(data_dir, _parse_quoted_list(args.remove))
    else:
        old, pos = _take_quoted(args.rename, 0)
        if args.rename[pos : pos + 2] != "->":
            raise ValidationError("rename expects old->new")
        new, _ = _take_quoted(args.rename, pos + 2)
        rename_topic(data_dir, old, new)
    _emit({"ok": True}, args.output)
    return 0
