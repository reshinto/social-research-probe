"""Helpers for the canonical emitted report envelope."""

from __future__ import annotations

from typing import Literal, TypedDict

from social_research_probe.utils.core.types import ReportPayload

ReportKind = Literal["synthesis", "suggestions", "corroboration"]


class ReportEnvelope(TypedDict):
    """Top-level envelope emitted by CLI commands that return a report.

    The project passes this data as dictionaries, so the type documents the keys that stages,
    services, and renderers are allowed to rely on.

    Examples:
        Input:
            ReportEnvelope
        Output:
            {"title": "Example"}
    """

    kind: ReportKind
    report: ReportPayload


def wrap_report(report: ReportPayload, kind: ReportKind) -> ReportEnvelope:
    """Document the wrap report rule at the boundary where callers use it.

    This utility is shared across commands, services, and stages, so the rule lives here instead of
    being reimplemented differently at each call site.

    Args:
        report: Research report dictionary being rendered, exported, or persisted.
        kind: Output kind or record category used to select the formatting branch.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            wrap_report(
                report={"topic": "AI safety", "items_top_n": []},
                kind="AI safety",
            )
        Output:
            "AI safety"
    """
    return {"kind": kind, "report": report}


def unwrap_report(payload: object) -> object:
    """Build the small payload that carries report through this workflow.

    This utility is shared across commands, services, and stages, so the rule lives here instead of
    being reimplemented differently at each call site.

    Args:
        payload: Input payload at this service, technology, or pipeline boundary.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            unwrap_report(
                payload={"title": "Example", "url": "https://youtu.be/demo"},
            )
        Output:
            "AI safety"
    """
    if (
        isinstance(payload, dict)
        and isinstance(payload.get("kind"), str)
        and isinstance(payload.get("report"), dict)
    ):
        return payload["report"]
    return payload
