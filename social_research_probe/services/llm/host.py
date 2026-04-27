from __future__ import annotations

import json
import sys
from typing import Literal

from social_research_probe.utils.core.report import wrap_report

ReportKind = Literal["synthesis", "suggestions", "corroboration"]


def emit_report(report: dict, kind: ReportKind) -> None:
    json.dump(wrap_report(report, kind), sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    sys.stdout.flush()
