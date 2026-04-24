"""Command: apply-pending. Promote pending suggestions into topics/purposes."""

from __future__ import annotations

import argparse
from pathlib import Path


def run(args: argparse.Namespace, data_dir: Path) -> int:
    from social_research_probe.cli.utils import _emit, _id_selector
    from social_research_probe.utils.command_models.suggestions import apply_pending

    apply_pending(
        data_dir,
        topic_ids=_id_selector(args.topics),
        purpose_ids=_id_selector(args.purposes),
    )
    _emit({"ok": True}, args.output)
    return 0
