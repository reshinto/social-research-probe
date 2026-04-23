"""Command handlers for topics, purposes, suggestions, config, and skill commands."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from social_research_probe.commands import config as config_cmd
from social_research_probe.commands import purposes as purposes_cmd
from social_research_probe.commands import suggestions as suggestions_cmd
from social_research_probe.commands import topics as topics_cmd
from social_research_probe.commands.parse import _parse_quoted_list, _take_quoted
from social_research_probe.errors import ValidationError

from .utils import _emit, _id_selector


def _handle_update_topics(args: argparse.Namespace, data_dir: Path) -> int:
    if args.add:
        topics_cmd.add_topics(data_dir, _parse_quoted_list(args.add), force=args.force)
    elif args.remove:
        topics_cmd.remove_topics(data_dir, _parse_quoted_list(args.remove))
    else:
        old, pos = _take_quoted(args.rename, 0)
        if args.rename[pos : pos + 2] != "->":
            raise ValidationError("rename expects old->new")
        new, _ = _take_quoted(args.rename, pos + 2)
        topics_cmd.rename_topic(data_dir, old, new)
    _emit({"ok": True}, args.output)
    return 0


def _handle_show_topics(args: argparse.Namespace, data_dir: Path) -> int:
    _emit({"topics": topics_cmd.show_topics(data_dir)}, args.output)
    return 0


def _handle_update_purposes(args: argparse.Namespace, data_dir: Path) -> int:
    if args.add:
        name, pos = _take_quoted(args.add, 0)
        if args.add[pos : pos + 1] != "=":
            raise ValidationError('add expects "name"="method"')
        method, _ = _take_quoted(args.add, pos + 1)
        purposes_cmd.add_purpose(data_dir, name=name, method=method, force=args.force)
    elif args.remove:
        purposes_cmd.remove_purposes(data_dir, _parse_quoted_list(args.remove))
    else:
        old, pos = _take_quoted(args.rename, 0)
        if args.rename[pos : pos + 2] != "->":
            raise ValidationError("rename expects old->new")
        new, _ = _take_quoted(args.rename, pos + 2)
        purposes_cmd.rename_purpose(data_dir, old, new)
    _emit({"ok": True}, args.output)
    return 0


def _handle_show_purposes(args: argparse.Namespace, data_dir: Path) -> int:
    _emit({"purposes": purposes_cmd.show_purposes(data_dir)}, args.output)
    return 0


def _handle_suggest_topics(args: argparse.Namespace, data_dir: Path) -> int:
    drafts = suggestions_cmd.suggest_topics(data_dir, count=args.count)
    suggestions_cmd.stage_suggestions(data_dir, topic_candidates=drafts, purpose_candidates=[])
    _emit({"staged_topic_suggestions": drafts}, args.output)
    return 0


def _handle_suggest_purposes(args: argparse.Namespace, data_dir: Path) -> int:
    drafts = suggestions_cmd.suggest_purposes(data_dir, count=args.count)
    suggestions_cmd.stage_suggestions(data_dir, topic_candidates=[], purpose_candidates=drafts)
    _emit({"staged_purpose_suggestions": drafts}, args.output)
    return 0


def _handle_show_pending(args: argparse.Namespace, data_dir: Path) -> int:
    _emit(suggestions_cmd.show_pending(data_dir), args.output)
    return 0


def _handle_apply_pending(args: argparse.Namespace, data_dir: Path) -> int:
    suggestions_cmd.apply_pending(
        data_dir,
        topic_ids=_id_selector(args.topics),
        purpose_ids=_id_selector(args.purposes),
    )
    _emit({"ok": True}, args.output)
    return 0


def _handle_discard_pending(args: argparse.Namespace, data_dir: Path) -> int:
    suggestions_cmd.discard_pending(
        data_dir,
        topic_ids=_id_selector(args.topics),
        purpose_ids=_id_selector(args.purposes),
    )
    _emit({"ok": True}, args.output)
    return 0


def _handle_stage_suggestions(args: argparse.Namespace, data_dir: Path) -> int:
    if not args.from_stdin:
        raise ValidationError("stage-suggestions requires --from-stdin")
    try:
        payload = json.loads(sys.stdin.read())
    except json.JSONDecodeError as exc:
        raise ValidationError(f"invalid JSON from stdin: {exc}") from exc
    suggestions_cmd.stage_suggestions(
        data_dir,
        topic_candidates=payload.get("topic_candidates", []),
        purpose_candidates=payload.get("purpose_candidates", []),
    )
    _emit({"ok": True}, args.output)
    return 0


def _handle_corroborate_claims(args: argparse.Namespace, data_dir: Path) -> int:
    from social_research_probe.commands import corroborate_claims as cc_cmd

    backends = [b.strip() for b in args.backends.split(",") if b.strip()]
    return cc_cmd.run(args.input, backends, output_path=args.output)


def _handle_render(args: argparse.Namespace, data_dir: Path) -> int:
    from social_research_probe.commands import render as render_cmd

    return render_cmd.run(args.packet, output_dir=args.output_dir)


def _handle_install_skill(args: argparse.Namespace, data_dir: Path) -> int:
    from social_research_probe.commands import install_skill

    return install_skill.run(args.target)


def _handle_setup(args: argparse.Namespace, data_dir: Path) -> int:
    from social_research_probe.commands import setup as setup_cmd

    return setup_cmd.run(data_dir)


def _handle_report(args: argparse.Namespace, data_dir: Path) -> int:
    from social_research_probe.commands import report as report_cmd

    return report_cmd.run(
        args.packet,
        compiled_synthesis_path=args.compiled_synthesis_path,
        opportunity_analysis_path=args.opportunity_analysis_path,
        final_summary_path=args.final_summary_path,
        out_path=args.out,
        data_dir=data_dir,
    )


def _handle_serve_report(args: argparse.Namespace, data_dir: Path) -> int:
    from social_research_probe.commands import serve_report as serve_report_cmd

    return serve_report_cmd.run(
        args.report,
        host=args.host,
        port=args.port,
        voicebox_base=args.voicebox_base,
    )


def _handle_set_secret(args: argparse.Namespace, data_dir: Path) -> int:
    if args.from_stdin:
        value = sys.stdin.read().rstrip("\n")
    else:
        import getpass

        value = getpass.getpass(f"{args.name}: ")
    if not value:
        raise ValidationError("empty secret value")
    config_cmd.write_secret(data_dir, args.name, value)
    return 0


def _dispatch_config(args: argparse.Namespace, data_dir: Path) -> int:
    """Route config sub-actions to the appropriate config command."""
    if args.config_cmd == "show":
        print(config_cmd.show_config(data_dir))
        return 0
    if args.config_cmd == "path":
        print(f"config: {data_dir / 'config.toml'}")
        print(f"secrets: {data_dir / 'secrets.toml'}")
        return 0
    if args.config_cmd == "set":
        config_cmd.write_config_value(data_dir, args.key, args.value)
        return 0
    if args.config_cmd == "set-secret":
        return _handle_set_secret(args, data_dir)
    if args.config_cmd == "unset-secret":
        config_cmd.unset_secret(data_dir, args.name)
        return 0
    if args.config_cmd == "check-secrets":
        result = config_cmd.check_secrets(
            data_dir,
            needed_for=args.needed_for,
            platform=args.platform,
            corroboration=args.corroboration,
        )
        _emit(result, args.output)
        return 0
    return 2
