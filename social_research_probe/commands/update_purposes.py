"""Command: update-purposes. Add, remove, or rename purposes."""

from __future__ import annotations

import argparse
from pathlib import Path


def run(args: argparse.Namespace, data_dir: Path) -> int:
    from social_research_probe.cli.dsl_parser import _parse_quoted_list, _take_quoted
    from social_research_probe.utils.command_models.purposes import (
        add_purpose,
        remove_purposes,
        rename_purpose,
    )
    from social_research_probe.utils.core.errors import ValidationError
    from social_research_probe.utils.display.cli_output import _emit

    if args.add:
        name, pos = _take_quoted(args.add, 0)
        if args.add[pos : pos + 1] != "=":
            raise ValidationError('add expects "name"="method"')
        method, _ = _take_quoted(args.add, pos + 1)
        add_purpose(data_dir, name=name, method=method, force=args.force)
    elif args.remove:
        remove_purposes(data_dir, _parse_quoted_list(args.remove))
    else:
        old, pos = _take_quoted(args.rename, 0)
        if args.rename[pos : pos + 2] != "->":
            raise ValidationError("rename expects old->new")
        new, _ = _take_quoted(args.rename, pos + 2)
        rename_purpose(data_dir, old, new)
    _emit({"ok": True}, args.output)
    return 0
