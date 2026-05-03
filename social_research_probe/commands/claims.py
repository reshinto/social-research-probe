"""Claims query and review CLI command."""

from __future__ import annotations

import argparse


def run(args: argparse.Namespace) -> int:
    """Dispatch claims subcommands."""
    parser = getattr(args, "_claims_parser", None)
    if not getattr(args, "claims_cmd", None):
        if parser:
            parser.print_help()
        return 0

    from social_research_probe.commands import ClaimsSubcommand

    cmd = args.claims_cmd
    if cmd == ClaimsSubcommand.LIST:
        return _list(args)
    if cmd == ClaimsSubcommand.SHOW:
        return _show(args)
    if cmd == ClaimsSubcommand.STATS:
        return _stats(args)
    if cmd == ClaimsSubcommand.REVIEW:
        return _review(args)
    if cmd == ClaimsSubcommand.NOTE:
        return _note(args)
    return 1


def _list(args: argparse.Namespace) -> int:
    from social_research_probe.config import load_active_config
    from social_research_probe.technologies.persistence.sqlite.connection import open_connection
    from social_research_probe.technologies.persistence.sqlite.queries import query_claims
    from social_research_probe.technologies.persistence.sqlite.schema import ensure_schema
    from social_research_probe.utils.display.cli_output import emit

    db_path = load_active_config().database_path
    conn = open_connection(db_path)
    try:
        ensure_schema(conn, db_path)
        results = query_claims(
            conn,
            run_id=args.run_id,
            topic=args.topic,
            claim_type=args.claim_type,
            needs_review=args.needs_review,
            needs_corroboration=args.needs_corroboration,
            corroboration_status=args.corroboration_status,
            extraction_method=args.extraction_method,
            limit=args.limit,
        )
    finally:
        conn.close()
    emit(results, args.output)
    return 0


def _show(args: argparse.Namespace) -> int:
    from social_research_probe.config import load_active_config
    from social_research_probe.technologies.persistence.sqlite.connection import open_connection
    from social_research_probe.technologies.persistence.sqlite.queries import (
        get_claim,
        get_claim_notes,
        get_claim_reviews,
    )
    from social_research_probe.technologies.persistence.sqlite.schema import ensure_schema
    from social_research_probe.utils.display.cli_output import emit

    db_path = load_active_config().database_path
    conn = open_connection(db_path)
    try:
        ensure_schema(conn, db_path)
        claim = get_claim(conn, args.claim_id)
        if claim is None:
            emit({"error": f"Claim '{args.claim_id}' not found"}, args.output)
            return 1
        claim_pk = claim["id"]
        claim["reviews"] = get_claim_reviews(conn, claim_pk)
        claim["notes"] = get_claim_notes(conn, claim_pk)
    finally:
        conn.close()
    emit(claim, args.output)
    return 0


def _stats(args: argparse.Namespace) -> int:
    from social_research_probe.config import load_active_config
    from social_research_probe.technologies.persistence.sqlite.connection import open_connection
    from social_research_probe.technologies.persistence.sqlite.queries import claim_stats
    from social_research_probe.technologies.persistence.sqlite.schema import ensure_schema
    from social_research_probe.utils.display.cli_output import emit

    db_path = load_active_config().database_path
    conn = open_connection(db_path)
    try:
        ensure_schema(conn, db_path)
        stats = claim_stats(conn)
    finally:
        conn.close()
    emit(stats, args.output)
    return 0


_VALID_STATUSES = frozenset({"unreviewed", "verified", "rejected", "disputed", "ignored"})
_VALID_IMPORTANCE = frozenset({"low", "medium", "high", "critical"})


def _review(args: argparse.Namespace) -> int:
    from social_research_probe.config import load_active_config
    from social_research_probe.technologies.persistence.sqlite.connection import open_connection
    from social_research_probe.technologies.persistence.sqlite.queries import (
        get_claim,
        upsert_claim_review,
    )
    from social_research_probe.technologies.persistence.sqlite.schema import ensure_schema
    from social_research_probe.utils.claims.quality import compute_quality_score
    from social_research_probe.utils.display.cli_output import emit

    if args.status not in _VALID_STATUSES:
        emit(
            {"error": f"Invalid status '{args.status}'. Valid: {sorted(_VALID_STATUSES)}"},
            args.output,
        )
        return 1
    if args.importance and args.importance not in _VALID_IMPORTANCE:
        emit(
            {
                "error": f"Invalid importance '{args.importance}'. Valid: {sorted(_VALID_IMPORTANCE)}"
            },
            args.output,
        )
        return 1

    db_path = load_active_config().database_path
    conn = open_connection(db_path)
    try:
        ensure_schema(conn, db_path)
        claim = get_claim(conn, args.claim_id)
        if claim is None:
            emit({"error": f"Claim '{args.claim_id}' not found"}, args.output)
            return 1
        claim_pk = claim["id"]
        quality_score = compute_quality_score(claim)
        upsert_claim_review(
            conn,
            claim_pk,
            claim_id=args.claim_id,
            run_id=claim["run_id"],
            review_status=args.status,
            review_note=args.notes,
            importance=args.importance,
            quality_score=quality_score,
        )
    finally:
        conn.close()
    emit({"ok": True, "claim_id": args.claim_id, "status": args.status}, args.output)
    return 0


def _note(args: argparse.Namespace) -> int:
    from social_research_probe.config import load_active_config
    from social_research_probe.technologies.persistence.sqlite.connection import open_connection
    from social_research_probe.technologies.persistence.sqlite.queries import (
        get_claim,
        insert_claim_note,
    )
    from social_research_probe.technologies.persistence.sqlite.schema import ensure_schema
    from social_research_probe.utils.display.cli_output import emit

    if not args.text.strip():
        emit({"error": "Note text must not be empty"}, args.output)
        return 1

    db_path = load_active_config().database_path
    conn = open_connection(db_path)
    try:
        ensure_schema(conn, db_path)
        claim = get_claim(conn, args.claim_id)
        if claim is None:
            emit({"error": f"Claim '{args.claim_id}' not found"}, args.output)
            return 1
        claim_pk = claim["id"]
        insert_claim_note(
            conn,
            claim_pk,
            claim_id=args.claim_id,
            run_id=claim["run_id"],
            note_text=args.text,
        )
    finally:
        conn.close()
    emit({"ok": True, "claim_id": args.claim_id, "note": args.text}, args.output)
    return 0
