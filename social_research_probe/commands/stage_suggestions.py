"""Command: stage-suggestions. Read JSON from stdin and stage candidates."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def run(args: argparse.Namespace, data_dir: Path) -> int:
    from social_research_probe.utils.command_models.suggestions import stage_suggestions
    from social_research_probe.utils.core.errors import ValidationError
    from social_research_probe.utils.display.cli_output import _emit

    if not args.from_stdin:
        raise ValidationError("stage-suggestions requires --from-stdin")
    try:
        payload = json.loads(sys.stdin.read())
    except json.JSONDecodeError as exc:
        raise ValidationError(f"invalid JSON from stdin: {exc}") from exc
    stage_suggestions(
        data_dir,
        topic_candidates=payload.get("topic_candidates", []),
        purpose_candidates=payload.get("purpose_candidates", []),
    )
    _emit({"ok": True}, args.output)
    return 0
