"""Command: suggest-purposes. Generate and stage new purpose suggestions."""

from __future__ import annotations

import argparse
from pathlib import Path


def run(args: argparse.Namespace, data_dir: Path) -> int:
    from social_research_probe.utils.command_models.suggestions import (
        stage_suggestions,
        suggest_purposes,
    )
    from social_research_probe.utils.display.cli_output import _emit

    drafts = suggest_purposes(data_dir, count=args.count)
    stage_suggestions(data_dir, topic_candidates=[], purpose_candidates=drafts)
    _emit({"staged_purpose_suggestions": drafts}, args.output)
    return 0
