"""Command: discard-pending. Remove entries from pending suggestions."""

from __future__ import annotations

import argparse

from social_research_probe.utils.core.exit_codes import ExitCode


def run(args: argparse.Namespace) -> int:
    from social_research_probe.commands import load_pending, save_pending, select_pending
    from social_research_probe.utils.cli.parsing import _id_selector
    from social_research_probe.utils.display.cli_output import emit

    pending = load_pending()
    _, remaining_topics = select_pending(
        pending["pending_topic_suggestions"], _id_selector(args.topics)
    )
    _, remaining_purposes = select_pending(
        pending["pending_purpose_suggestions"], _id_selector(args.purposes)
    )
    pending["pending_topic_suggestions"] = remaining_topics
    pending["pending_purpose_suggestions"] = remaining_purposes
    save_pending(pending)
    emit({"ok": True}, args.output)
    return ExitCode.SUCCESS
