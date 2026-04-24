"""Command: apply-pending. Promote pending suggestions into topics/purposes."""

from __future__ import annotations

import argparse
from pathlib import Path


def run(args: argparse.Namespace, data_dir: Path) -> int:
    from social_research_probe.utils.cli import _id_selector
    from social_research_probe.utils.command_models.suggestions import apply_pending
    from social_research_probe.utils.display.cli_output import _emit

    apply_pending(
        data_dir,
        topic_ids=_id_selector(args.topics),
        purpose_ids=_id_selector(args.purposes),
    )
    _emit({"ok": True}, args.output)
    return 0
