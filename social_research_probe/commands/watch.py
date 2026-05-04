"""srp watch subcommand: local-first monitors and alert events."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path

from social_research_probe.utils.core.errors import ValidationError
from social_research_probe.utils.core.exit_codes import ExitCode
from social_research_probe.utils.monitoring.defaults import DEFAULT_ALERT_RULES


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _open_db(require_persistence: bool = False) -> tuple[object, object]:
    from social_research_probe.config import load_active_config
    from social_research_probe.technologies.persistence.sqlite.connection import open_connection
    from social_research_probe.technologies.persistence.sqlite.schema import ensure_schema

    cfg = load_active_config()
    db_cfg = cfg.raw.get("database") or {}
    if not db_cfg.get("enabled", True):
        raise ValidationError("watch commands require database.enabled=true")
    if require_persistence:
        _ensure_persistence_enabled(cfg)
    conn = open_connection(cfg.database_path)
    ensure_schema(conn, db_path=cfg.database_path)
    return conn, cfg


def _ensure_persistence_enabled(cfg: object) -> None:
    if not cfg.technology_enabled("sqlite_persist"):
        raise ValidationError("srp watch run requires technologies.sqlite_persist=true")
    if not cfg.service_enabled("sqlite"):
        raise ValidationError("srp watch run requires services.persistence.sqlite=true")


def _ensure_watch_persist_stage(cfg: object, platform: str) -> None:
    if not cfg.stage_enabled(platform, "persist"):
        raise ValidationError(f"srp watch run requires stages.{platform}.persist=true")


def _parse_purposes(args: argparse.Namespace) -> list[str]:
    purposes = [p.strip() for p in getattr(args, "purposes", []) if p.strip()]
    if not purposes:
        raise ValidationError("watch add requires at least one --purpose")
    return purposes


def _parse_topic(args: argparse.Namespace) -> str:
    topic = getattr(args, "topic", "").strip()
    if not topic:
        raise ValidationError("watch add requires a non-empty --topic")
    return topic


def _parse_platform(args: argparse.Namespace) -> str:
    from social_research_probe.platforms import PIPELINES

    platform = getattr(args, "platform", "").strip()
    supported = sorted(p for p in PIPELINES if p != "all")
    if platform not in supported:
        raise ValidationError(
            f"unsupported watch platform: {platform!r}; expected one of {supported}"
        )
    return platform


def _parse_rules(raw_rules: list[str]) -> list[dict]:
    from social_research_probe.utils.monitoring.alerts import parse_alert_rule_json

    if not raw_rules:
        return [dict(rule) for rule in DEFAULT_ALERT_RULES]
    return [dict(parse_alert_rule_json(raw)) for raw in raw_rules]


def _generate_watch_id(conn: object, topic: str, platform: str, purposes: list[str]) -> str:
    from social_research_probe.technologies.persistence.sqlite.watch_repository import get_watch

    digest = hashlib.sha256(f"{platform}|{topic}|{','.join(purposes)}".encode()).hexdigest()[:8]
    base = f"watch-{_slug(topic)}-{digest}"
    candidate = base
    suffix = 2
    while get_watch(conn, candidate) is not None:
        candidate = f"{base}-{suffix}"
        suffix += 1
    return candidate


def _slug(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:36] or "topic"


def _add_watch(args: argparse.Namespace) -> int:
    from social_research_probe.technologies.persistence.sqlite.watch_repository import (
        get_watch,
        insert_watch,
    )

    conn, _cfg = _open_db()
    try:
        topic = _parse_topic(args)
        platform = _parse_platform(args)
        purposes = _parse_purposes(args)
        rules = _parse_rules(getattr(args, "alert_rules", []))
        watch_id = _generate_watch_id(conn, topic, platform, purposes)
        now = _now()
        with conn:
            insert_watch(
                conn,
                watch_id=watch_id,
                topic=topic,
                platform=platform,
                purposes=purposes,
                enabled=not getattr(args, "disabled", False),
                interval=getattr(args, "interval", None),
                alert_rules=rules,
                output_dir=getattr(args, "output_dir", None),
                created_at=now,
                updated_at=now,
            )
        watch = get_watch(conn, watch_id)
    finally:
        conn.close()
    _print_watch_result(watch, args)
    return ExitCode.SUCCESS


def _list_watches(args: argparse.Namespace) -> int:
    from social_research_probe.technologies.persistence.sqlite.watch_repository import list_watches

    conn, _cfg = _open_db()
    try:
        watches = list_watches(conn, enabled_only=getattr(args, "enabled", False))
    finally:
        conn.close()
    _print_watch_result(watches, args)
    return ExitCode.SUCCESS


def _remove_watch(args: argparse.Namespace) -> int:
    from social_research_probe.technologies.persistence.sqlite.watch_repository import remove_watch

    conn, _cfg = _open_db()
    try:
        with conn:
            removed = remove_watch(conn, args.watch_id)
    finally:
        conn.close()
    if removed == 0:
        raise ValidationError(f"watch not found: {args.watch_id}")
    _print_watch_result({"removed": args.watch_id}, args)
    return ExitCode.SUCCESS


def _list_alerts(args: argparse.Namespace) -> int:
    from social_research_probe.technologies.persistence.sqlite.watch_repository import (
        list_alert_events,
    )

    conn, _cfg = _open_db()
    try:
        alerts = list_alert_events(
            conn, watch_id=getattr(args, "watch_id", None), limit=getattr(args, "limit", 100)
        )
    finally:
        conn.close()
    _print_alert_result(alerts, args)
    return ExitCode.SUCCESS


def _run_watches(args: argparse.Namespace) -> int:
    conn, cfg = _open_db(require_persistence=True)
    try:
        watches = _select_watches(conn, args)
        summaries = [_execute_watch(conn, cfg, watch, args) for watch in watches]
    finally:
        conn.close()
    _print_run_result(summaries, args)
    return ExitCode.ERROR if any(s["status"] == "failed" for s in summaries) else ExitCode.SUCCESS


def _select_watches(conn: object, args: argparse.Namespace) -> list[dict]:
    from social_research_probe.technologies.persistence.sqlite.watch_repository import (
        get_watch,
        list_watches,
    )

    watch_id = getattr(args, "watch_id", None)
    if watch_id:
        watch = get_watch(conn, watch_id)
        if watch is None:
            raise ValidationError(f"watch not found: {watch_id}")
        return [watch]
    return list_watches(conn, enabled_only=True)


def _execute_watch(conn: object, cfg: object, watch: dict, args: argparse.Namespace) -> dict:
    watch_run_id = _new_id("watchrun")
    started_at = _now()
    try:
        _ensure_watch_persist_stage(cfg, watch["platform"])
        return _execute_watch_success(conn, cfg, watch, args, watch_run_id, started_at)
    except Exception as exc:
        _record_failed_watch_run(conn, watch, watch_run_id, started_at, exc)
        return _failure_summary(watch, watch_run_id, started_at, exc)


def _execute_watch_success(
    conn: object,
    cfg: object,
    watch: dict,
    args: argparse.Namespace,
    watch_run_id: str,
    started: str,
) -> dict:
    from social_research_probe.commands.research import run_research_for_watch

    report = run_research_for_watch(watch["platform"], watch["topic"], tuple(watch["purposes"]))
    target_run_id = _target_run_id(report)
    target_row = _get_target_run(conn, target_run_id)
    baseline_row = _resolve_baseline(conn, watch, target_run_id)
    return _complete_watch_run(
        conn, cfg, watch, args, watch_run_id, started, target_row, baseline_row
    )


def _complete_watch_run(
    conn: object,
    cfg: object,
    watch: dict,
    args: argparse.Namespace,
    watch_run_id: str,
    started: str,
    target_row: dict,
    baseline_row: dict | None,
) -> dict:
    comparison, artifacts = _compare_if_possible(conn, cfg, watch, args, target_row, baseline_row)
    alert_count = _persist_alerts(conn, cfg, watch, comparison, artifacts) if comparison else 0
    finished = _now()
    with conn:
        _insert_success_run(
            conn, watch, watch_run_id, started, finished, target_row, baseline_row, artifacts
        )
        _update_watch_state(conn, watch, target_row, finished)
    return _success_summary(watch, watch_run_id, target_row, baseline_row, alert_count, artifacts)


def _compare_if_possible(
    conn: object,
    cfg: object,
    watch: dict,
    args: argparse.Namespace,
    target: dict,
    baseline: dict | None,
) -> tuple[dict | None, dict[str, str]]:
    if baseline is None:
        return None, {}
    from social_research_probe.utils.comparison.export import write_comparison_artifacts
    from social_research_probe.utils.comparison.runner import build_comparison

    comparison = build_comparison(conn, baseline, target)
    output_dir = _comparison_output_dir(cfg, watch, args)
    if output_dir is None:
        return comparison, {}
    return comparison, write_comparison_artifacts(comparison, output_dir)


def _persist_alerts(
    conn: object, cfg: object, watch: dict, comparison: dict, artifacts: dict[str, str]
) -> int:
    from social_research_probe.technologies.persistence.sqlite.comparison_queries import (
        count_claims_needing_review,
    )
    from social_research_probe.utils.monitoring.alerts import evaluate_alert_rules

    target_pk = comparison["target"]["run_pk"]
    extra = {"claims_needing_review": count_claims_needing_review(conn, target_pk)}
    matched = evaluate_alert_rules(comparison, watch["alert_rules"], extra)
    if not matched:
        return 0
    alert = _build_alert_event(cfg, watch, comparison, matched, artifacts)
    _write_and_insert_alert(conn, cfg, watch, alert)
    return 1


def _build_alert_event(
    cfg: object, watch: dict, comparison: dict, matched: list[dict], artifacts: dict[str, str]
) -> dict:
    from social_research_probe.utils.monitoring.alerts import (
        build_alert_message,
        build_alert_title,
        max_severity,
    )

    alert = {
        "alert_id": _new_id("alert"),
        "watch_id": watch["watch_id"],
        "baseline_run_id": comparison["baseline"]["run_id"],
        "target_run_id": comparison["target"]["run_id"],
        "created_at": _now(),
        "severity": max_severity(matched),
        "matched_rules": matched,
        "trend_signals": comparison.get("trends") or [],
        "artifact_paths": dict(artifacts),
        "acknowledged": False,
    }
    alert["title"] = build_alert_title(watch, matched)
    alert["message"] = build_alert_message(watch, matched)
    return alert


def _write_and_insert_alert(conn: object, cfg: object, watch: dict, alert: dict) -> None:
    from social_research_probe.technologies.persistence.sqlite.watch_repository import (
        insert_alert_event,
    )
    from social_research_probe.utils.monitoring.export import write_alert_artifacts

    try:
        alert["artifact_paths"].update(write_alert_artifacts(alert, _alert_output_dir(cfg, watch)))
    except Exception as exc:
        alert["artifact_paths"]["alert_export_error"] = f"{exc.__class__.__name__}: {exc}"
    with conn:
        insert_alert_event(conn, **alert)


def _get_target_run(conn: object, target_run_id: str) -> dict:
    from social_research_probe.technologies.persistence.sqlite.comparison_queries import (
        get_run_by_text_id,
    )

    target = get_run_by_text_id(conn, target_run_id)
    if target is None:
        raise ValidationError(f"persisted target run not found: {target_run_id}")
    return target


def _resolve_baseline(conn: object, watch: dict, target_run_id: str) -> dict | None:
    from social_research_probe.technologies.persistence.sqlite.comparison_queries import (
        get_previous_matching_run,
        get_run_by_text_id,
    )
    from social_research_probe.technologies.persistence.sqlite.watch_repository import (
        latest_successful_watch_run,
    )

    baseline_id = watch.get("last_target_run_id")
    if baseline_id and baseline_id != target_run_id:
        baseline = get_run_by_text_id(conn, baseline_id)
        if baseline is not None:
            return baseline
    watch_id = watch.get("watch_id")
    if watch_id:
        prior_run = latest_successful_watch_run(conn, watch_id)
        prior_target_id = prior_run.get("target_run_id") if prior_run else None
        if prior_target_id and prior_target_id != target_run_id:
            baseline = get_run_by_text_id(conn, prior_target_id)
            if baseline is not None:
                return baseline
    return get_previous_matching_run(
        conn, topic=watch["topic"], platform=watch["platform"], target_run_id=target_run_id
    )


def _target_run_id(report: dict) -> str:
    run_id = report.get("run_id")
    if isinstance(run_id, str) and run_id:
        return run_id
    raise ValidationError("persistence did not produce target run_id for watch run")


def _insert_success_run(
    conn: object,
    watch: dict,
    watch_run_id: str,
    started: str,
    finished: str,
    target: dict,
    baseline: dict | None,
    artifacts: dict[str, str],
) -> None:
    from social_research_probe.technologies.persistence.sqlite.watch_repository import (
        insert_watch_run,
    )

    insert_watch_run(
        conn,
        watch_run_id=watch_run_id,
        watch_id=watch["watch_id"],
        baseline_run_id=baseline.get("run_id") if baseline else None,
        target_run_id=target["run_id"],
        started_at=started,
        finished_at=finished,
        status="success",
        error_kind=None,
        error_message=None,
        comparison_artifacts=artifacts,
    )


def _update_watch_state(conn: object, watch: dict, target: dict, finished: str) -> None:
    from social_research_probe.technologies.persistence.sqlite.watch_repository import (
        update_watch_after_run,
    )

    update_watch_after_run(
        conn,
        watch_id=watch["watch_id"],
        last_run_at=finished,
        last_target_run_id=target["run_id"],
        updated_at=finished,
    )


def _record_failed_watch_run(
    conn: object, watch: dict, watch_run_id: str, started_at: str, exc: Exception
) -> None:
    from social_research_probe.technologies.persistence.sqlite.watch_repository import (
        insert_watch_run,
    )

    with conn:
        insert_watch_run(
            conn,
            watch_run_id=watch_run_id,
            watch_id=watch["watch_id"],
            baseline_run_id=watch.get("last_target_run_id"),
            target_run_id=None,
            started_at=started_at,
            finished_at=_now(),
            status="failed",
            error_kind=exc.__class__.__name__,
            error_message=str(exc),
            comparison_artifacts={},
        )


def _comparison_output_dir(cfg: object, watch: dict, args: argparse.Namespace) -> Path | None:
    raw = getattr(args, "export_dir", None) or watch.get("output_dir")
    return _resolve_output_dir(cfg, raw, "comparisons") if raw else None


def _alert_output_dir(cfg: object, watch: dict) -> Path:
    return _resolve_output_dir(cfg, watch.get("output_dir"), "alerts")


def _resolve_output_dir(cfg: object, raw: str | None, default_child: str) -> Path:
    base = Path(raw).expanduser() if raw else cfg.data_dir / default_child
    return base if base.is_absolute() else cfg.data_dir / base


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _success_summary(
    watch: dict,
    watch_run_id: str,
    target: dict,
    baseline: dict | None,
    alert_count: int,
    artifacts: dict[str, str],
) -> dict:
    return {
        "watch_run_id": watch_run_id,
        "watch_id": watch["watch_id"],
        "status": "success",
        "baseline_run_id": baseline.get("run_id") if baseline else None,
        "target_run_id": target["run_id"],
        "alert_count": alert_count,
        "comparison_artifacts": artifacts,
    }


def _failure_summary(watch: dict, watch_run_id: str, started_at: str, exc: Exception) -> dict:
    return {
        "watch_run_id": watch_run_id,
        "watch_id": watch["watch_id"],
        "status": "failed",
        "started_at": started_at,
        "error_kind": exc.__class__.__name__,
        "error_message": str(exc),
    }


def _print_watch_result(data: object, args: argparse.Namespace) -> None:
    output = getattr(args, "output", "text")
    if output == "json":
        print(json.dumps(data, indent=2, default=str))
    elif output == "markdown":
        print(_format_watch_markdown(data))
    else:
        print(_format_watch_text(data))


def _print_alert_result(alerts: list[dict], args: argparse.Namespace) -> None:
    output = getattr(args, "output", "text")
    if output == "json":
        print(json.dumps(alerts, indent=2, default=str))
    elif output == "markdown":
        print(_format_alert_markdown(alerts))
    else:
        print(_format_alert_text(alerts))


def _print_run_result(summaries: list[dict], args: argparse.Namespace) -> None:
    output = getattr(args, "output", "text")
    if output == "json":
        print(json.dumps(summaries, indent=2, default=str))
    else:
        print(_format_run_text(summaries))


def _format_watch_text(data: object) -> str:
    if isinstance(data, list):
        return "\n".join(_watch_line(watch) for watch in data) or "No watches found."
    if isinstance(data, dict) and "removed" in data:
        return f"Removed watch {data['removed']}"
    return _watch_line(data) if isinstance(data, dict) else str(data)


def _watch_line(watch: dict) -> str:
    enabled = "enabled" if watch.get("enabled", True) else "disabled"
    purposes = ",".join(watch.get("purposes") or [])
    return f"{watch['watch_id']}  {enabled}  {watch['platform']}  {watch['topic']}  {purposes}"


def _format_watch_markdown(data: object) -> str:
    if isinstance(data, list):
        lines = ["| Watch ID | Status | Platform | Topic | Purposes |", "|---|---|---|---|---|"]
        lines.extend(_watch_md_row(watch) for watch in data)
        return "\n".join(lines)
    return _format_watch_text(data)


def _watch_md_row(watch: dict) -> str:
    enabled = "enabled" if watch.get("enabled", True) else "disabled"
    purposes = ", ".join(watch.get("purposes") or [])
    return f"| `{watch['watch_id']}` | {enabled} | {watch['platform']} | {watch['topic']} | {purposes} |"


def _format_alert_text(alerts: list[dict]) -> str:
    if not alerts:
        return "No alerts found."
    return "\n".join(
        f"{a['alert_id']}  {a.get('severity') or 'info'}  {a['watch_id']}  {a.get('title') or ''}"
        for a in alerts
    )


def _format_alert_markdown(alerts: list[dict]) -> str:
    if not alerts:
        return "No alerts found."
    lines = ["| Alert ID | Severity | Watch | Title |", "|---|---|---|---|"]
    lines.extend(
        f"| `{a['alert_id']}` | {a.get('severity') or 'info'} | `{a['watch_id']}` | {a.get('title') or ''} |"
        for a in alerts
    )
    return "\n".join(lines)


def _format_run_text(summaries: list[dict]) -> str:
    if not summaries:
        return "No enabled watches found."
    lines = []
    for item in summaries:
        if item["status"] == "failed":
            lines.append(f"{item['watch_id']} failed: {item['error_message']}")
        else:
            lines.append(
                f"{item['watch_id']} ok: target={item['target_run_id']} alerts={item['alert_count']}"
            )
    return "\n".join(lines)


def run(args: argparse.Namespace) -> int:
    """Dispatch watch subcommands."""
    from social_research_probe.commands import WatchSubcommand

    if not getattr(args, "watch_cmd", None):
        parser = getattr(args, "_watch_parser", None)
        if parser:
            parser.print_help()
        return ExitCode.SUCCESS
    if args.watch_cmd == WatchSubcommand.ADD:
        return _add_watch(args)
    if args.watch_cmd == WatchSubcommand.LIST:
        return _list_watches(args)
    if args.watch_cmd == WatchSubcommand.REMOVE:
        return _remove_watch(args)
    if args.watch_cmd == WatchSubcommand.RUN:
        return _run_watches(args)
    if args.watch_cmd == WatchSubcommand.ALERTS:
        return _list_alerts(args)
    return ExitCode.ERROR
