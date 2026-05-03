"""Command: show-purposes. Print the current purposes registry."""

from __future__ import annotations

import argparse

from social_research_probe.utils.core.exit_codes import ExitCode


def _load_purposes() -> dict:
    """Load and return the current purposes registry as a plain dict.

    Command helpers keep user-facing parsing, validation, and output formatting out of the pipeline
    and service layers.

    Returns:
        Dictionary with stable keys consumed by downstream project code.

    Examples:
        Input:
            _load_purposes()
        Output:
            {"enabled": True}
    """
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
    """Build the small payload that carries purposes through this workflow.

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
    from social_research_probe.utils.display.cli_output import emit

    emit({"purposes": _load_purposes()}, args.output)
    return ExitCode.SUCCESS
