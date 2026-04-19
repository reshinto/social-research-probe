"""CLI entry point — thin argparse shell that delegates to command modules."""

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
from social_research_probe.config import resolve_data_dir
from social_research_probe.errors import SrpError, ValidationError


def _add_topics_subparsers(sub: argparse._SubParsersAction) -> None:
    """Register update-topics and show-topics subcommands."""
    ut = sub.add_parser("update-topics")
    group = ut.add_mutually_exclusive_group(required=True)
    group.add_argument("--add")
    group.add_argument("--remove")
    group.add_argument("--rename")
    ut.add_argument("--force", action="store_true")
    ut.add_argument("--output", choices=["text", "json", "markdown"], default="text")
    st = sub.add_parser("show-topics")
    st.add_argument("--output", choices=["text", "json", "markdown"], default="text")


def _add_purposes_subparsers(sub: argparse._SubParsersAction) -> None:
    """Register update-purposes and show-purposes subcommands."""
    up = sub.add_parser("update-purposes")
    group = up.add_mutually_exclusive_group(required=True)
    group.add_argument("--add")
    group.add_argument("--remove")
    group.add_argument("--rename")
    up.add_argument("--force", action="store_true")
    up.add_argument("--output", choices=["text", "json", "markdown"], default="text")
    sp = sub.add_parser("show-purposes")
    sp.add_argument("--output", choices=["text", "json", "markdown"], default="text")


def _add_suggestions_subparsers(sub: argparse._SubParsersAction) -> None:
    """Register all suggestion-related subcommands."""
    sug_t = sub.add_parser("suggest-topics")
    sug_t.add_argument("--count", type=int, default=5)
    sug_t.add_argument("--output", choices=["text", "json", "markdown"], default="text")
    sug_p = sub.add_parser("suggest-purposes")
    sug_p.add_argument("--count", type=int, default=5)
    sug_p.add_argument("--output", choices=["text", "json", "markdown"], default="text")
    show_pend = sub.add_parser("show-pending")
    show_pend.add_argument("--output", choices=["text", "json", "markdown"], default="text")
    ap = sub.add_parser("apply-pending")
    ap.add_argument("--topics", default="")
    ap.add_argument("--purposes", default="")
    ap.add_argument("--output", choices=["text", "json", "markdown"], default="text")
    dp = sub.add_parser("discard-pending")
    dp.add_argument("--topics", default="")
    dp.add_argument("--purposes", default="")
    dp.add_argument("--output", choices=["text", "json", "markdown"], default="text")
    ss = sub.add_parser("stage-suggestions")
    ss.add_argument("--from-stdin", action="store_true")
    ss.add_argument("--output", choices=["text", "json", "markdown"], default="text")


def _add_research_subparsers(sub: argparse._SubParsersAction) -> None:
    """Register research, corroboration, render, and install-skill subcommands."""
    rs = sub.add_parser(
        "research",
        help="Simple form: research [platform] TOPIC PURPOSES (purposes comma-separated)",
    )
    rs.add_argument("args", nargs="+", help="[PLATFORM] TOPIC PURPOSE[,PURPOSE...]")
    rs.add_argument("--mode", choices=["skill", "cli"], default="cli")
    rs.add_argument(
        "--no-shorts", action="store_true", help="Exclude YouTube Shorts (<90s) from results"
    )
    rs.add_argument(
        "--no-transcripts",
        action="store_true",
        help="Skip transcript fetching for top-5 items (faster, less context)",
    )
    cc = sub.add_parser("corroborate-claims", help="Corroborate claims from a JSON file")
    cc.add_argument("--input", required=True, help="Path to claims JSON file")
    cc.add_argument("--backends", default="llm_cli", help="Comma-separated backend names")
    cc.add_argument("--output", default=None, help="Output file path (default: stdout)")
    rend = sub.add_parser("render", help="Render charts and stats for a research packet")
    rend.add_argument("--packet", required=True, help="Path to packet JSON file")
    rend.add_argument("--output-dir", default=None, help="Directory to save charts")
    ins = sub.add_parser("install-skill", help="Copy skill files into ~/.claude/skills/srp")
    ins.add_argument("--target", default=None, help="Destination (default: ~/.claude/skills/srp)")


def _add_config_subparsers(sub: argparse._SubParsersAction) -> None:
    """Register the config subcommand with its own sub-actions."""
    cfg = sub.add_parser("config")
    cfg_sub = cfg.add_subparsers(dest="config_cmd", metavar="ACTION")
    cfg_show = cfg_sub.add_parser("show")
    cfg_show.add_argument("--output", choices=["text", "json", "markdown"], default="text")
    cfg_path = cfg_sub.add_parser("path")
    cfg_path.add_argument("--output", choices=["text", "json", "markdown"], default="text")
    set_p = cfg_sub.add_parser("set")
    set_p.add_argument("key")
    set_p.add_argument("value")
    set_p.add_argument("--output", choices=["text", "json", "markdown"], default="text")
    sec_p = cfg_sub.add_parser("set-secret")
    sec_p.add_argument("name")
    sec_p.add_argument("--from-stdin", action="store_true")
    sec_p.add_argument("--output", choices=["text", "json", "markdown"], default="text")
    unset_p = cfg_sub.add_parser("unset-secret")
    unset_p.add_argument("name")
    unset_p.add_argument("--output", choices=["text", "json", "markdown"], default="text")
    check_p = cfg_sub.add_parser("check-secrets")
    check_p.add_argument("--needed-for", default=None)
    check_p.add_argument("--platform", default=None)
    check_p.add_argument("--corroboration", default=None)
    check_p.add_argument("--output", choices=["text", "json", "markdown"], default="text")


def _global_parser() -> argparse.ArgumentParser:
    """Build and return the root argument parser."""
    parser = argparse.ArgumentParser(
        prog="srp", description="Evidence-first social-media research."
    )
    parser.add_argument("--mode", choices=["skill", "cli"], default="cli")
    parser.add_argument("--data-dir", default=None)
    parser.add_argument("--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    _add_topics_subparsers(sub)
    _add_purposes_subparsers(sub)
    _add_suggestions_subparsers(sub)
    _add_research_subparsers(sub)
    _add_config_subparsers(sub)
    return parser


def _emit(data: object, fmt: str) -> None:
    """Write *data* to stdout in the requested format."""
    if fmt == "json":
        json.dump(data, sys.stdout)
        sys.stdout.write("\n")
    elif fmt == "markdown":
        sys.stdout.write(_to_markdown(data) + "\n")
    else:
        sys.stdout.write(_to_text(data) + "\n")


def _to_text(data: object) -> str:
    if isinstance(data, dict) and "topics" in data:
        return "\n".join(data["topics"]) if data["topics"] else "(no topics)"
    if isinstance(data, dict) and "purposes" in data:
        if not data["purposes"]:
            return "(no purposes)"
        return "\n".join(f"{k}: {v['method']}" for k, v in data["purposes"].items())
    if isinstance(data, str):
        return data
    return json.dumps(data, indent=2)


def _to_markdown(data: object) -> str:
    return "```\n" + _to_text(data) + "\n```"


def _id_selector(raw: str):
    """Parse a comma-separated id list or the literal ``all``."""
    if not raw:
        return []
    if raw == "all":
        return "all"
    try:
        return [int(x.strip()) for x in raw.split(",") if x.strip()]
    except ValueError as exc:
        raise ValidationError(f"invalid id selector: {raw!r}") from exc


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


def _handle_research(args: argparse.Namespace, data_dir: Path) -> int:
    """Simple positional form. Examples:

    srp research ai latest-news                 # platform defaults to youtube
    srp research youtube ai latest-news
    srp research youtube ai latest-news,trends  # multiple purposes
    """
    import sys

    from social_research_probe.commands.parse import parse
    from social_research_probe.pipeline import run_research
    from social_research_probe.synthesize.formatter import render_full

    platform, topic, purposes = _parse_simple_research_args(args.args)
    config_extras = {
        "include_shorts": not args.no_shorts,
        "fetch_transcripts": not args.no_transcripts,
    }
    raw = f'run-research platform:{platform} "{topic}"->{"+".join(purposes)}'
    packet = run_research(parse(raw), data_dir, args.mode, adapter_config=config_extras)
    if args.mode == "cli":
        sys.stdout.write(render_full(packet))
    return 0


def _parse_simple_research_args(positional: list[str]) -> tuple[str, str, list[str]]:
    """Parse [platform] topic purposes into (platform, topic, purposes)."""
    known_platforms = {"youtube"}
    if len(positional) < 2:
        raise ValidationError("research needs at least TOPIC and PURPOSES")
    if positional[0] in known_platforms and len(positional) >= 3:
        platform, topic, purpose_arg = positional[0], positional[1], positional[2]
    else:
        platform, topic, purpose_arg = "youtube", positional[0], positional[1]
    purposes = [p.strip() for p in purpose_arg.split(",") if p.strip()]
    if not purposes:
        raise ValidationError("research needs at least one purpose")
    return platform, topic, purposes


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


_HANDLERS = {
    "update-topics": _handle_update_topics,
    "show-topics": _handle_show_topics,
    "update-purposes": _handle_update_purposes,
    "show-purposes": _handle_show_purposes,
    "suggest-topics": _handle_suggest_topics,
    "suggest-purposes": _handle_suggest_purposes,
    "show-pending": _handle_show_pending,
    "apply-pending": _handle_apply_pending,
    "discard-pending": _handle_discard_pending,
    "stage-suggestions": _handle_stage_suggestions,
    "research": _handle_research,
    "corroborate-claims": _handle_corroborate_claims,
    "render": _handle_render,
    "install-skill": _handle_install_skill,
    "config": lambda args, data_dir: _dispatch_config(args, data_dir),
}


def _dispatch(args: argparse.Namespace) -> int:
    """Route parsed args to the appropriate command handler."""
    data_dir = resolve_data_dir(args.data_dir)
    handler = _HANDLERS.get(args.command)
    if handler is None:
        return 2
    return handler(args, data_dir)


def main(argv: list[str] | None = None) -> int:
    """Parse argv and dispatch to the matching subcommand."""
    parser = _global_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help(sys.stderr)
        return 2
    try:
        return _dispatch(args)
    except SrpError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return exc.exit_code


if __name__ == "__main__":
    sys.exit(main())
