"""SQLite persistence technology — writes a completed research run to srp.db."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import ClassVar

from social_research_probe.technologies import BaseTechnology
from social_research_probe.technologies.persistence.sqlite.connection import (
    open_connection,
)
from social_research_probe.technologies.persistence.sqlite.repository import (
    derive_run_id,
    derive_source_key,
    insert_artifacts,
    insert_comments,
    insert_run,
    insert_snapshot,
    insert_text_surrogate,
    insert_transcript,
    insert_warnings,
    upsert_source,
)
from social_research_probe.technologies.persistence.sqlite.schema import (
    SCHEMA_VERSION,
    ensure_schema,
)
from social_research_probe.utils.pipeline.helpers import resolve_html_report_path


def _config_snapshot(config: dict) -> dict:
    """Return a whitelisted config subset safe to persist."""
    snapshot: dict = {}
    if "database" in config:
        snapshot["database"] = config["database"]
    if "scoring" in config:
        snapshot["scoring"] = {"weights": (config["scoring"] or {}).get("weights") or {}}
    platforms = config.get("platforms") or {}
    youtube = platforms.get("youtube") or {}
    if youtube:
        snapshot["platforms"] = {
            "youtube": {k: v for k, v in youtube.items() if not isinstance(v, dict)}
        }
    return snapshot


class SQLitePersistTech(BaseTechnology[dict, dict]):
    """Write a completed research run to the local SQLite database."""

    name: ClassVar[str] = "sqlite_persist"
    enabled_config_key: ClassVar[str] = "sqlite_persist"
    cacheable: ClassVar[bool] = False

    async def _execute(self, data: dict) -> dict:
        report: dict = data.get("report") or {}
        db_path: Path = Path(data["db_path"])
        config: dict = data.get("config") or {}
        persist_transcript_text: bool = bool(data.get("persist_transcript_text", False))
        persist_comment_text: bool = bool(data.get("persist_comment_text", True))

        now = datetime.now(UTC).isoformat()
        items: list[dict] = [it for it in (report.get("items_top_n") or []) if isinstance(it, dict)]
        warnings_raw: list = report.get("warnings") or []
        export_paths: dict[str, str] = report.get("export_paths") or {}

        html_path = resolve_html_report_path(report)
        html_report_path_str = str(html_path) if html_path else None
        output_dir = str(html_path.parent) if html_path else None
        run_id = derive_run_id(report)

        conn = open_connection(db_path)
        try:
            ensure_schema(conn)
            with conn:
                run_pk = insert_run(
                    conn,
                    run_id=run_id,
                    topic=report.get("topic") or "",
                    platform=report.get("platform") or "youtube",
                    purpose_set=report.get("purpose_set") or [],
                    started_at=now,
                    finished_at=now,
                    html_report_path=html_report_path_str,
                    output_dir=output_dir,
                    export_paths=export_paths,
                    warning_count=len(warnings_raw),
                    exit_status="partial" if warnings_raw else "ok",
                    config_snapshot=_config_snapshot(config),
                    schema_version=SCHEMA_VERSION,
                )

                source_count = 0
                comment_count = 0
                for item in items:
                    platform, external_id = derive_source_key(item)
                    surrogate: dict = item.get("text_surrogate") or {}
                    source_pk = upsert_source(
                        conn,
                        platform=platform,
                        external_id=external_id,
                        url=item.get("url") or "",
                        title=item.get("title"),
                        description=surrogate.get("description"),
                        channel=item.get("channel"),
                        source_class=item.get("source_class"),
                        published_at=item.get("published_at"),
                        now=now,
                    )
                    source_count += 1

                    snap_pk = insert_snapshot(
                        conn,
                        source_pk=source_pk,
                        run_pk=run_pk,
                        item=item,
                        observed_at=now,
                    )

                    source_comments: list[dict] = item.get("source_comments") or []
                    comment_count += insert_comments(
                        conn,
                        snap_pk,
                        source_comments,
                        persist_text=persist_comment_text,
                    )

                    insert_transcript(
                        conn,
                        snap_pk,
                        item,
                        persist_text=persist_transcript_text,
                    )

                    if surrogate:
                        insert_text_surrogate(conn, snap_pk, surrogate)

                insert_warnings(conn, run_pk, warnings_raw)
                insert_artifacts(
                    conn,
                    run_pk,
                    html_report_path=html_report_path_str,
                    export_paths=export_paths,
                    created_at=now,
                )
        finally:
            conn.close()

        return {
            "db_path": str(db_path),
            "run_pk": run_pk,
            "run_id": run_id,
            "persisted_source_count": source_count,
            "persisted_comment_count": comment_count,
        }
