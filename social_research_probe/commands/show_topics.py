"""Command: show-topics. Print the current topics list."""

from __future__ import annotations

import argparse

from social_research_probe.utils.core.exit_codes import ExitCode

_TOPICS_FILENAME = "topics.json"


def _load_topics() -> list[str]:
    """Load and return the current topics list from state."""
    from social_research_probe.config import load_active_config
    from social_research_probe.utils.state.migrate import migrate_to_current
    from social_research_probe.utils.state.schemas import TOPICS_SCHEMA, default_topics
    from social_research_probe.utils.state.store import read_json
    from social_research_probe.utils.state.validate import validate

    data_dir = load_active_config().data_dir
    path = data_dir / _TOPICS_FILENAME
    data = read_json(path, default_factory=default_topics)
    data = migrate_to_current(path, data, kind="topics")
    validate(data, TOPICS_SCHEMA)
    return list(data["topics"])


def run(args: argparse.Namespace) -> int:
    from social_research_probe.utils.display.cli_output import emit

    emit({"topics": _load_topics()}, args.output)
    return ExitCode.SUCCESS
