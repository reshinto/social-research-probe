"""Command: suggest-topics. Generate and stage new topic suggestions."""

from __future__ import annotations

import argparse
from pathlib import Path


def run(args: argparse.Namespace, data_dir: Path) -> int:
    from social_research_probe.utils.command_models.suggestions import (
        stage_suggestions,
        suggest_topics,
    )
    from social_research_probe.utils.display.cli_output import _emit

    drafts = suggest_topics(data_dir, count=args.count)
    stage_suggestions(data_dir, topic_candidates=drafts, purpose_candidates=[])
    _emit({"staged_topic_suggestions": drafts}, args.output)
    return 0
