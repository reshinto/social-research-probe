"""Command: stage-suggestions. Read JSON from stdin and stage candidates."""

from __future__ import annotations

import argparse
import json
import sys

from social_research_probe.utils.core.exit_codes import ExitCode


def run(args: argparse.Namespace) -> int:
    from social_research_probe.commands import add_pending_suggestions
    from social_research_probe.utils.core.errors import ValidationError
    from social_research_probe.utils.display.cli_output import emit

    if not args.from_stdin:
        raise ValidationError("stage-suggestions requires --from-stdin")
    try:
        payload = json.loads(sys.stdin.read())
    except json.JSONDecodeError as exc:
        raise ValidationError(f"invalid JSON from stdin: {exc}") from exc
    add_pending_suggestions(
        topic_candidates=payload.get("topic_candidates", []),
        purpose_candidates=payload.get("purpose_candidates", []),
    )
    emit({"ok": True}, args.output)
    return ExitCode.SUCCESS
