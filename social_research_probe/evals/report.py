"""JSON + Markdown writers for EvalReport artifacts.

The harness writes two files per run under ``.srp-eval/<service_id>/``:

- ``<timestamp>.json`` — full structured record (consumed by the trend
  chart generator and downstream tooling).
- ``<timestamp>.md`` — human-readable summary used by Phase 11 docs and
  on-call triage.

No plotting import is forced at module load — callers that don't need a
trend chart avoid pulling in matplotlib.
"""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from pathlib import Path


def _to_dict(obj: object) -> object:
    """Recursively convert dataclasses to dicts for JSON serialisation."""
    if is_dataclass(obj) and not isinstance(obj, type):
        return {k: _to_dict(v) for k, v in asdict(obj).items()}
    if isinstance(obj, dict):
        return {k: _to_dict(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_dict(v) for v in obj]
    return obj


def write_json(report: object, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_to_dict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def write_markdown(report_dict: dict, path: Path) -> Path:
    """Write a human-readable Markdown summary of the eval run."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append(f"# Reliability eval — {report_dict['service_id']}")
    lines.append("")
    lines.append(f"- Timestamp: {report_dict['timestamp']}")
    lines.append(f"- Generator runner: {report_dict.get('generator_runner', 'n/a')}")
    lines.append(f"- Judge runner: {report_dict.get('judge_runner', 'skipped')}")
    lines.append(f"- Samples: {report_dict['runs']}")
    lines.append("")
    lines.append("## Gate outcomes")
    lines.append("")
    gates = report_dict.get("gates", [])
    if gates:
        lines.append("| Gate | Threshold | Observed | Result |")
        lines.append("|---|---|---|---|")
        for g in gates:
            marker = "✅" if g["passed"] else "❌"
            lines.append(f"| {g['name']} | {g['threshold']} | {g['observed']} | {marker} |")
    lines.append("")
    lines.append("## Per-sample outcomes")
    lines.append("")
    for i, s in enumerate(report_dict.get("samples", []), start=1):
        lines.append(f"### Sample {i}")
        lines.append("")
        lines.append(f"- Coverage: {s.get('coverage', 0):.3f}")
        lines.append(f"- Hallucinations: {s.get('hallucinations', [])}")
        lines.append(f"- Length OK: {s.get('length_ok', False)}")
        judge = s.get("judge")
        if judge:
            lines.append(
                "- Judge: "
                f"faithfulness={judge.get('faithfulness')}, "
                f"completeness={judge.get('completeness')}, "
                f"clarity={judge.get('clarity')}, "
                f"conciseness={judge.get('conciseness')}"
            )
        lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def timestamp_now() -> str:
    """Return a filename-safe UTC timestamp suitable for artifact paths."""
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
