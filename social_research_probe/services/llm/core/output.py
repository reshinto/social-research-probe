"""Core output support.

It owns the service-level orchestration for this capability, leaving provider details to technology adapters.
"""

from __future__ import annotations

import json
import sys
from typing import Literal

from social_research_probe.utils.core.report import wrap_report

ReportKind = Literal["synthesis", "suggestions", "corroboration"]


def emit_report(report: dict, kind: ReportKind) -> None:
    """Write the report payload in the output mode requested by the caller.

    Services translate platform data into adapter calls and normalize the result so stages can
    handle success, skip, and failure consistently.

    Args:
        report: Research report dictionary being rendered, exported, or persisted.
        kind: Output kind or record category used to select the formatting branch.

    Returns:
        None. The result is communicated through state mutation, file/database writes, output, or an
        exception.

    Examples:
        Input:
            emit_report(
                report={"topic": "AI safety", "items_top_n": []},
                kind="AI safety",
            )
        Output:
            None
    """
    json.dump(wrap_report(report, kind), sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    sys.stdout.flush()
