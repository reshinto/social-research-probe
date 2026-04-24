"""Command: discard-pending. Remove entries from pending suggestions."""

from __future__ import annotations

import argparse
from pathlib import Path


def run(args: argparse.Namespace, data_dir: Path) -> int:
    from social_research_probe.utils.display.cli_output import _emit
    from social_research_probe.utils.cli import _id_selector
    from social_research_probe.utils.command_models.suggestions import discard_pending

    discard_pending(
        data_dir,
        topic_ids=_id_selector(args.topics),
        purpose_ids=_id_selector(args.purposes),
    )
    _emit({"ok": True}, args.output)
    return 0
