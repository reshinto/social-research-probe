"""Command: apply-pending. Promote pending suggestions into topics/purposes."""

from __future__ import annotations

import argparse

from social_research_probe.utils.core.exit_codes import ExitCode


def run(args: argparse.Namespace) -> int:
    from social_research_probe.commands import (
        add_purpose,
        add_topics,
        load_pending,
        save_pending,
        select_pending,
    )
    from social_research_probe.utils.cli.parsing import _id_selector
    from social_research_probe.utils.core.errors import DuplicateError
    from social_research_probe.utils.display.cli_output import emit

    pending = load_pending()
    chosen_topics, remaining_topics = select_pending(
        pending["pending_topic_suggestions"], _id_selector(args.topics)
    )
    chosen_purposes, remaining_purposes = select_pending(
        pending["pending_purpose_suggestions"], _id_selector(args.purposes)
    )

    for entry in chosen_topics:
        try:
            add_topics([entry["value"]], force=False)
        except DuplicateError:
            pass

    for entry in chosen_purposes:
        try:
            add_purpose(name=entry["name"], method=entry["method"], force=False)
        except DuplicateError:
            pass

    pending["pending_topic_suggestions"] = remaining_topics
    pending["pending_purpose_suggestions"] = remaining_purposes
    save_pending(pending)
    emit({"ok": True}, args.output)
    return ExitCode.SUCCESS
