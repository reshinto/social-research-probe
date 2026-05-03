"""Tests for claims CLI wiring: Command enum, parser, handler factory."""

from __future__ import annotations

from social_research_probe.cli.handlers import handlers_factory
from social_research_probe.cli.parsers import global_parser
from social_research_probe.commands import ClaimsSubcommand, Command


def test_command_claims_in_strenum():
    assert Command.CLAIMS == "claims"
    assert Command.CLAIMS in Command


def test_claims_subcommand_values():
    assert ClaimsSubcommand.LIST == "list"
    assert ClaimsSubcommand.SHOW == "show"
    assert ClaimsSubcommand.STATS == "stats"
    assert ClaimsSubcommand.REVIEW == "review"
    assert ClaimsSubcommand.NOTE == "note"


def test_parser_creates_claims_subparser():
    parser = global_parser()
    args = parser.parse_args(["claims", "list", "--needs-review"])
    assert args.command == "claims"
    assert args.claims_cmd == "list"
    assert args.needs_review is True


def test_parser_claims_list_has_all_filter_args():
    parser = global_parser()
    args = parser.parse_args(
        [
            "claims",
            "list",
            "--run-id",
            "5",
            "--topic",
            "AI",
            "--claim-type",
            "fact_claim",
            "--needs-review",
            "--needs-corroboration",
            "--corroboration-status",
            "pending",
            "--extraction-method",
            "llm",
            "--limit",
            "50",
            "--output",
            "json",
        ]
    )
    assert args.run_id == 5
    assert args.topic == "AI"
    assert args.claim_type == "fact_claim"
    assert args.needs_review is True
    assert args.needs_corroboration is True
    assert args.corroboration_status == "pending"
    assert args.extraction_method == "llm"
    assert args.limit == 50
    assert args.output == "json"


def test_parser_claims_show_has_claim_id():
    parser = global_parser()
    args = parser.parse_args(["claims", "show", "abc123"])
    assert args.claims_cmd == "show"
    assert args.claim_id == "abc123"


def test_parser_claims_review_has_required_args():
    parser = global_parser()
    args = parser.parse_args(
        [
            "claims",
            "review",
            "abc123",
            "--status",
            "verified",
            "--importance",
            "high",
            "--notes",
            "checked source",
        ]
    )
    assert args.claims_cmd == "review"
    assert args.claim_id == "abc123"
    assert args.status == "verified"
    assert args.importance == "high"
    assert args.notes == "checked source"


def test_parser_claims_note_has_args():
    parser = global_parser()
    args = parser.parse_args(["claims", "note", "abc123", "some note text"])
    assert args.claims_cmd == "note"
    assert args.claim_id == "abc123"
    assert args.text == "some note text"


def test_handler_factory_has_claims():
    handlers = handlers_factory()
    assert Command.CLAIMS in handlers


def test_no_subcommand_prints_help(capsys):
    parser = global_parser()
    args = parser.parse_args(["claims"])
    from social_research_probe.commands import claims

    result = claims.run(args)
    assert result == 0


def test_dispatch_claims_calls_module():
    from social_research_probe.cli.handlers import _dispatch_claims

    parser = global_parser()
    args = parser.parse_args(["claims"])
    result = _dispatch_claims(args)
    assert result == 0
