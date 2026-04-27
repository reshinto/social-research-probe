"""Helpers for the canonical emitted report envelope."""

from __future__ import annotations

from typing import Literal, TypedDict

from social_research_probe.utils.core.types import ReportPayload

ReportKind = Literal["synthesis", "suggestions", "corroboration"]


class ReportEnvelope(TypedDict):
    """Top-level envelope emitted by CLI commands that return a report."""

    kind: ReportKind
    report: ReportPayload


def wrap_report(report: ReportPayload, kind: ReportKind) -> ReportEnvelope:
    """Return the canonical emitted envelope for *report*."""
    return {"kind": kind, "report": report}


def unwrap_report(payload: object) -> object:
    """Return the inner report when *payload* is an emitted envelope."""
    if (
        isinstance(payload, dict)
        and isinstance(payload.get("kind"), str)
        and isinstance(payload.get("report"), dict)
    ):
        return payload["report"]
    return payload
