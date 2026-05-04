"""Write local alert summary artifacts."""

from __future__ import annotations

import json
from pathlib import Path


def write_alert_artifacts(alert: dict, output_dir: Path) -> dict[str, str]:
    """Write JSON and Markdown alert summaries."""
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = alert["alert_id"]
    json_path = output_dir / f"{stem}.json"
    md_path = output_dir / f"{stem}.md"
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(alert, f, indent=2, default=str)
    md_path.write_text(_format_markdown(alert), encoding="utf-8")
    return {"alert_json": str(json_path), "alert_markdown": str(md_path)}


def _format_markdown(alert: dict) -> str:
    lines = [
        f"# {alert.get('title') or 'Monitoring Alert'}",
        "",
        f"- Watch: `{alert.get('watch_id')}`",
        f"- Severity: `{alert.get('severity')}`",
        f"- Baseline run: `{alert.get('baseline_run_id') or ''}`",
        f"- Target run: `{alert.get('target_run_id') or ''}`",
        "",
        alert.get("message") or "",
        "",
        "## Matched Rules",
    ]
    for rule in alert.get("matched_rules") or []:
        lines.append(f"- `{rule['metric']} {rule['op']} {rule['value']}` actual `{rule['actual']}`")
    return "\n".join(lines).rstrip() + "\n"
