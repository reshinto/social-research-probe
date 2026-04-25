"""Command: apply-pending. Promote pending suggestions into topics/purposes."""

from __future__ import annotations

import argparse

from social_research_probe.utils.core.exit_codes import ExitCode


def _select_from_pending(pending: dict, args: argparse.Namespace) -> tuple:
    """Select chosen and remaining entries based on CLI selectors."""
    from social_research_probe.commands import select_pending
    from social_research_probe.utils.cli.parsing import _id_selector

    chosen_topics, remaining_topics = select_pending(
        pending["pending_topic_suggestions"], _id_selector(args.topics)
    )
    chosen_purposes, remaining_purposes = select_pending(
        pending["pending_purpose_suggestions"], _id_selector(args.purposes)
    )
    return chosen_topics, remaining_topics, chosen_purposes, remaining_purposes


def _apply_topic_entries(chosen_topics: list) -> None:
    """Add each chosen topic, silently skipping duplicates."""
    from social_research_probe.commands import add_topics
    from social_research_probe.utils.core.errors import DuplicateError

    for entry in chosen_topics:
        try:
            add_topics([entry["value"]], force=False)
        except DuplicateError:
            pass


def _apply_purpose_entries(chosen_purposes: list) -> None:
    """Add each chosen purpose, silently skipping duplicates."""
    from social_research_probe.commands import add_purpose
    from social_research_probe.utils.core.errors import DuplicateError

    for entry in chosen_purposes:
        try:
            add_purpose(name=entry["name"], method=entry["method"], force=False)
        except DuplicateError:
            pass


def _commit_pending(pending: dict, remaining_topics: list, remaining_purposes: list) -> None:
    """Update the pending state with remaining entries and persist."""
    from social_research_probe.commands import save_pending

    pending["pending_topic_suggestions"] = remaining_topics
    pending["pending_purpose_suggestions"] = remaining_purposes
    save_pending(pending)


def run(args: argparse.Namespace) -> int:
    from social_research_probe.commands import load_pending
    from social_research_probe.utils.display.cli_output import emit

    pending = load_pending()
    chosen_topics, remaining_topics, chosen_purposes, remaining_purposes = _select_from_pending(pending, args)
    _apply_topic_entries(chosen_topics)
    _apply_purpose_entries(chosen_purposes)
    _commit_pending(pending, remaining_topics, remaining_purposes)
    emit({"ok": True}, args.output)
    return ExitCode.SUCCESS
