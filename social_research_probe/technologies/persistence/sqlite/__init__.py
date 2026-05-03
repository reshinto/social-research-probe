"""SQLite persistence technology — writes a completed research run to srp.db."""

from __future__ import annotations

import sqlite3
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
    insert_claims,
    insert_comments,
    insert_narratives,
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
    """Return a whitelisted config subset safe to persist.

    Persistence helpers keep database schema decisions at the storage boundary instead of spreading

    SQL-shaped data through the pipeline.

    Args:
        config: Configuration or context values that control this run.

    Returns:
        Dictionary with stable keys consumed by downstream project code.

    Examples:
        Input:
            _config_snapshot(
                config={"enabled": True},
            )
        Output:
            {"enabled": True}
    """
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
    """Write a completed research run to the local SQLite database.

    Examples:
        Input:
            SQLitePersistTech
        Output:
            SQLitePersistTech
    """

    name: ClassVar[str] = "sqlite_persist"
    enabled_config_key: ClassVar[str] = "sqlite_persist"
    cacheable: ClassVar[bool] = False

    async def _execute(self, data: dict) -> dict:
        """Document the execute rule at the boundary where callers use it.

        The caller gets one stable method even when this component needs fallbacks or provider-specific
        handling.

        Args:
            data: Input payload at this service, technology, or pipeline boundary.

        Returns:
            Dictionary with stable keys consumed by downstream project code.

        Examples:
            Input:
                await _execute(
                    data={"title": "Example", "url": "https://youtu.be/demo"},
                )
            Output:
                {"enabled": True}
        """
        report, db_path, config, persist_transcript_text, persist_comment_text = (
            self._extract_payload(data)
        )
        ctx = self._resolve_run_context(report)
        conn = open_connection(db_path)
        try:
            ensure_schema(conn)
            run_pk, source_count, comment_count = self._run_transaction(
                conn, report, ctx, config, persist_comment_text, persist_transcript_text
            )
        finally:
            conn.close()
        return {
            "db_path": str(db_path),
            "run_pk": run_pk,
            "run_id": ctx["run_id"],
            "persisted_source_count": source_count,
            "persisted_comment_count": comment_count,
        }

    def _extract_payload(self, data: dict) -> tuple[dict, Path, dict, bool, bool]:
        """Build the small payload that carries db_path through this workflow.

        Persistence helpers keep database schema decisions at the storage boundary instead of spreading
        SQL-shaped data through the pipeline.

        Args:
            data: Input payload at this service, technology, or pipeline boundary.

        Returns:
            Tuple whose positions are part of the public helper contract shown in the example.

        Examples:
            Input:
                _extract_payload(
                    data={"title": "Example", "url": "https://youtu.be/demo"},
                )
            Output:
                Path("report.html")
        """
        report: dict = data.get("report") or {}
        db_path: Path = Path(data["db_path"])
        config: dict = data.get("config") or {}
        persist_transcript_text: bool = bool(data.get("persist_transcript_text", False))
        persist_comment_text: bool = bool(data.get("persist_comment_text", True))
        return report, db_path, config, persist_transcript_text, persist_comment_text

    def _resolve_run_context(self, report: dict) -> dict:
        """Document the resolve run context rule at the boundary where callers use it.

        Persistence helpers keep database schema decisions at the storage boundary instead of spreading

        SQL-shaped data through the pipeline.

        Args:
            report: Research report dictionary being rendered, exported, or persisted.

        Returns:
            Dictionary with stable keys consumed by downstream project code.

        Examples:
            Input:
                _resolve_run_context(
                    report={"topic": "AI safety", "items_top_n": []},
                )
            Output:
                {"enabled": True}
        """
        html_path = resolve_html_report_path(report)
        return {
            "now": datetime.now(UTC).isoformat(),
            "items": [it for it in (report.get("items_top_n") or []) if isinstance(it, dict)],
            "warnings_raw": report.get("warnings") or [],
            "narratives": report.get("narratives") or [],
            "export_paths": report.get("export_paths") or {},
            "html_report_path_str": str(html_path) if html_path else None,
            "output_dir": str(html_path.parent) if html_path else None,
            "run_id": derive_run_id(report),
        }

    def _insert_run_record(
        self, conn: sqlite3.Connection, report: dict, ctx: dict, config: dict
    ) -> int:
        """Document the insert run record rule at the boundary where callers use it.

        Persistence helpers keep database schema decisions at the storage boundary instead of spreading

        SQL-shaped data through the pipeline.

        Args:
            conn: Open SQLite connection for the current transaction.
            report: Research report dictionary being rendered, exported, or persisted.
            ctx: Configuration or context values that control this run.
            config: Configuration or context values that control this run.

        Returns:
            Integer count, limit, status code, or timeout used by the caller.

        Examples:
            Input:
                _insert_run_record(
                    conn=sqlite3.Connection(":memory:"),
                    report={"topic": "AI safety", "items_top_n": []},
                    ctx={"enabled": True},
                    config={"enabled": True},
                )
            Output:
                5
        """
        return insert_run(
            conn,
            run_id=ctx["run_id"],
            topic=report.get("topic") or "",
            platform=report.get("platform") or "youtube",
            purpose_set=report.get("purpose_set") or [],
            started_at=ctx["now"],
            finished_at=ctx["now"],
            html_report_path=ctx["html_report_path_str"],
            output_dir=ctx["output_dir"],
            export_paths=ctx["export_paths"],
            warning_count=len(ctx["warnings_raw"]),
            exit_status="partial" if ctx["warnings_raw"] else "ok",
            config_snapshot=_config_snapshot(config),
            schema_version=SCHEMA_VERSION,
        )

    def _upsert_item_source(
        self, conn: sqlite3.Connection, item: dict, surrogate: dict, now: str
    ) -> int:
        """Insert or update item source in SQLite.

        Keeping SQL details here lets pipeline code work with project records instead of database
        plumbing.

        Args:
            conn: Open SQLite connection for the current transaction.
            item: Single source item, database row, or registry entry being transformed.
            surrogate: Text surrogate payload that represents the source content available for later
                       stages.
            now: Timestamp used for recency filtering, age calculations, or persisted audit metadata.

        Returns:
            Integer count, limit, status code, or timeout used by the caller.

        Examples:
            Input:
                _upsert_item_source(
                    conn=sqlite3.Connection(":memory:"),
                    item={"title": "Example", "url": "https://youtu.be/demo"},
                    surrogate={"primary_text": "Demo transcript"},
                    now=datetime(2026, 1, 1),
                )
            Output:
                5
        """
        platform, external_id = derive_source_key(item)
        return upsert_source(
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

    def _persist_item(
        self,
        conn: sqlite3.Connection,
        item: dict,
        run_pk: int,
        now: str,
        persist_comment_text: bool,
        persist_transcript_text: bool,
    ) -> int:
        """Document the persist item rule at the boundary where callers use it.

        Persistence helpers keep database schema decisions at the storage boundary instead of spreading

        SQL-shaped data through the pipeline.

        Args:
            conn: Open SQLite connection for the current transaction.
            item: Single source item, database row, or registry entry being transformed.
            run_pk: Count, database id, index, or limit that bounds the work being performed.
            now: Timestamp used for recency filtering, age calculations, or persisted audit metadata.
            persist_comment_text: Flag that selects the branch for this operation.
            persist_transcript_text: Flag that selects the branch for this operation.

        Returns:
            None. The result is communicated through state mutation, file/database writes, output, or an
            exception.

        Examples:
            Input:
                _persist_item(
                    conn=sqlite3.Connection(":memory:"),
                    item={"title": "Example", "url": "https://youtu.be/demo"},
                    run_pk=3,
                    now=datetime(2026, 1, 1),
                    persist_comment_text=True,
                    persist_transcript_text=True,
                )
            Output:
                None
        """
        surrogate: dict = item.get("text_surrogate") or {}
        source_pk = self._upsert_item_source(conn, item, surrogate, now)
        snap_pk = insert_snapshot(
            conn, source_pk=source_pk, run_pk=run_pk, item=item, observed_at=now
        )
        comment_count = insert_comments(
            conn, snap_pk, item.get("source_comments") or [], persist_text=persist_comment_text
        )
        insert_transcript(conn, snap_pk, item, persist_text=persist_transcript_text, fetched_at=now)
        if surrogate:
            insert_text_surrogate(conn, snap_pk, surrogate)
        insert_claims(
            conn,
            run_pk,
            snap_pk,
            source_pk,
            item.get("extracted_claims") or [],
            source_url=item.get("url") or "",
            source_title=item.get("title") or "",
            created_at=now,
        )
        return comment_count

    def _persist_items(
        self,
        conn: sqlite3.Connection,
        items: list[dict],
        run_pk: int,
        now: str,
        persist_comment_text: bool,
        persist_transcript_text: bool,
    ) -> tuple[int, int]:
        """Document the persist items rule at the boundary where callers use it.

        Persistence helpers keep database schema decisions at the storage boundary instead of spreading

        SQL-shaped data through the pipeline.

        Args:
            conn: Open SQLite connection for the current transaction.
            items: Ordered source items being carried through the current pipeline step.
            run_pk: Count, database id, index, or limit that bounds the work being performed.
            now: Timestamp used for recency filtering, age calculations, or persisted audit metadata.
            persist_comment_text: Flag that selects the branch for this operation.
            persist_transcript_text: Flag that selects the branch for this operation.

        Returns:
            None. The result is communicated through state mutation, file/database writes, output, or an
            exception.

        Examples:
            Input:
                _persist_items(
                    conn=sqlite3.Connection(":memory:"),
                    items=[{"title": "Example", "url": "https://youtu.be/demo"}],
                    run_pk=3,
                    now=datetime(2026, 1, 1),
                    persist_comment_text=True,
                    persist_transcript_text=True,
                )
            Output:
                None
        """
        source_count = 0
        comment_count = 0
        for item in items:
            comment_count += self._persist_item(
                conn, item, run_pk, now, persist_comment_text, persist_transcript_text
            )
            source_count += 1
        return source_count, comment_count

    def _run_transaction(
        self,
        conn: sqlite3.Connection,
        report: dict,
        ctx: dict,
        config: dict,
        persist_comment_text: bool,
        persist_transcript_text: bool,
    ) -> tuple[int, int, int]:
        """Document the run transaction rule at the boundary where callers use it.

        Persistence helpers keep database schema decisions at the storage boundary instead of spreading

        SQL-shaped data through the pipeline.

        Args:
            conn: Open SQLite connection for the current transaction.
            report: Research report dictionary being rendered, exported, or persisted.
            ctx: Configuration or context values that control this run.
            config: Configuration or context values that control this run.
            persist_comment_text: Flag that selects the branch for this operation.
            persist_transcript_text: Flag that selects the branch for this operation.

        Returns:
            Tuple whose positions are part of the public helper contract shown in the example.

        Examples:
            Input:
                _run_transaction(
                    conn=sqlite3.Connection(":memory:"),
                    report={"topic": "AI safety", "items_top_n": []},
                    ctx={"enabled": True},
                    config={"enabled": True},
                    persist_comment_text=True,
                    persist_transcript_text=True,
                )
            Output:
                ("AI safety", "Find unmet needs")
        """
        with conn:
            run_pk = self._insert_run_record(conn, report, ctx, config)
            source_count, comment_count = self._persist_items(
                conn,
                ctx["items"],
                run_pk,
                ctx["now"],
                persist_comment_text,
                persist_transcript_text,
            )
            insert_warnings(conn, run_pk, ctx["warnings_raw"])
            narratives = ctx.get("narratives") or []
            if narratives:
                insert_narratives(conn, run_pk, narratives, created_at=ctx["now"])
            insert_artifacts(
                conn,
                run_pk,
                html_report_path=ctx["html_report_path_str"],
                export_paths=ctx["export_paths"],
                created_at=ctx["now"],
            )
        return run_pk, source_count, comment_count
