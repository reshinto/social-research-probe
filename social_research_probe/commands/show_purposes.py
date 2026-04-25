"""Command: show-purposes. Print the current purposes registry."""

from __future__ import annotations

import argparse

from social_research_probe.utils.core.exit_codes import ExitCode


def _load_purposes() -> dict:
    """Load and return the current purposes registry as a plain dict."""
    from social_research_probe.utils.purposes import registry

    data = registry.load()
    return {
        name: {
            "method": entry["method"],
            "evidence_priorities": list(entry.get("evidence_priorities", [])),
            "scoring_overrides": dict(entry.get("scoring_overrides", {})),
        }
        for name, entry in data["purposes"].items()
    }


def run(args: argparse.Namespace) -> int:
    from social_research_probe.utils.display.cli_output import emit

    emit({"purposes": _load_purposes()}, args.output)
    return ExitCode.SUCCESS
