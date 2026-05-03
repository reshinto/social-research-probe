"""Command: apply-pending. Promote pending suggestions into topics/purposes."""

from __future__ import annotations

import argparse
import contextlib

from social_research_probe.utils.core.exit_codes import ExitCode


def _select_from_pending(pending: dict, args: argparse.Namespace) -> tuple:
    """Document the select from pending rule at the boundary where callers use it.

    Command helpers keep user-facing parsing, validation, and output formatting out of the pipeline
    and service layers.

    Args:
        pending: Intermediate collection used to preserve ordering while stage results are merged.
        args: Parsed argparse namespace for the command being dispatched.

    Returns:
        Tuple whose positions are part of the public helper contract shown in the example.

    Examples:
        Input:
            _select_from_pending(
                pending=[],
                args=argparse.Namespace(output="json"),
            )
        Output:
            ("AI safety", "Find unmet needs")
    """
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
    """Add each chosen topic, silently skipping duplicates.

    Command helpers keep user-facing parsing, validation, and output formatting out of the pipeline
    and service layers.

    Args:
        chosen_topics: Pending topic suggestions selected for application.

    Returns:
        None. The result is communicated through state mutation, file/database writes, output, or an
        exception.

    Examples:
        Input:
            _apply_topic_entries(
                chosen_topics=["AI safety"],
            )
        Output:
            None
    """
    from social_research_probe.commands import add_topics
    from social_research_probe.utils.core.errors import DuplicateError

    for entry in chosen_topics:
        with contextlib.suppress(DuplicateError):
            add_topics([entry["value"]], force=False)


def _apply_purpose_entries(chosen_purposes: list) -> None:
    """Add each chosen purpose, silently skipping duplicates.

    Command helpers keep user-facing parsing, validation, and output formatting out of the pipeline
    and service layers.

    Args:
        chosen_purposes: Pending purpose suggestions selected for application.

    Returns:
        None. The result is communicated through state mutation, file/database writes, output, or an
        exception.

    Examples:
        Input:
            _apply_purpose_entries(
                chosen_purposes=["AI safety"],
            )
        Output:
            None
    """
    from social_research_probe.commands import add_purpose
    from social_research_probe.utils.core.errors import DuplicateError

    for entry in chosen_purposes:
        with contextlib.suppress(DuplicateError):
            add_purpose(name=entry["name"], method=entry["method"], force=False)


def _commit_pending(pending: dict, remaining_topics: list, remaining_purposes: list) -> None:
    """Update the pending state with remaining entries and persist.

    Command helpers keep user-facing parsing, validation, and output formatting out of the pipeline
    and service layers.

    Args:
        pending: Intermediate collection used to preserve ordering while stage results are merged.
        remaining_topics: Pending topic suggestions left after the selected entries are applied.
        remaining_purposes: Pending purpose suggestions left after the selected entries are
                            applied.

    Returns:
        None. The result is communicated through state mutation, file/database writes, output, or an
        exception.

    Examples:
        Input:
            _commit_pending(
                pending=[],
                remaining_topics=["AI safety"],
                remaining_purposes=["AI safety"],
            )
        Output:
            None
    """
    from social_research_probe.commands import save_pending

    pending["pending_topic_suggestions"] = remaining_topics
    pending["pending_purpose_suggestions"] = remaining_purposes
    save_pending(pending)


def run(args: argparse.Namespace) -> int:
    """Build the small payload that carries ok through this workflow.

    This is the command boundary: argparse passes raw options in, and the rest of the application
    receives validated project data or a clear error.

    Args:
        args: Parsed argparse namespace for the command being dispatched.

    Returns:
        Integer count, limit, status code, or timeout used by the caller.

    Examples:
        Input:
            run(
                args=argparse.Namespace(output="json"),
            )
        Output:
            5
    """
    from social_research_probe.commands import load_pending
    from social_research_probe.utils.display.cli_output import emit

    pending = load_pending()
    chosen_topics, remaining_topics, chosen_purposes, remaining_purposes = _select_from_pending(
        pending, args
    )
    _apply_topic_entries(chosen_topics)
    _apply_purpose_entries(chosen_purposes)
    _commit_pending(pending, remaining_topics, remaining_purposes)
    emit({"ok": True}, args.output)
    return ExitCode.SUCCESS
