"""CLI entry point. All P1 subcommands wired up."""
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


def _global_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="srp", description="Evidence-first social-media research.")
    parser.add_argument("--mode", choices=["skill", "cli"], default="cli")
    parser.add_argument("--data-dir", default=None)
    parser.add_argument("--verbose", action="store_true")

    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    ut = sub.add_parser("update-topics")
    group = ut.add_mutually_exclusive_group(required=True)
    group.add_argument("--add")
    group.add_argument("--remove")
    group.add_argument("--rename")
    ut.add_argument("--force", action="store_true")
    ut.add_argument("--output", choices=["text", "json", "markdown"], default="text")

    st = sub.add_parser("show-topics")
    st.add_argument("--output", choices=["text", "json", "markdown"], default="text")

    up = sub.add_parser("update-purposes")
    group = up.add_mutually_exclusive_group(required=True)
    group.add_argument("--add")
    group.add_argument("--remove")
    group.add_argument("--rename")
    up.add_argument("--force", action="store_true")
    up.add_argument("--output", choices=["text", "json", "markdown"], default="text")

    sp = sub.add_parser("show-purposes")
    sp.add_argument("--output", choices=["text", "json", "markdown"], default="text")

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

    rr = sub.add_parser("run-research")
    rr.add_argument("--platform", required=True)
    rr.add_argument("--mode", choices=["skill", "cli"], default="cli")
    rr.add_argument("dsl", nargs="+")

    ins = sub.add_parser("install-skill", help="Copy SKILL.md + references into a target directory")
    ins.add_argument("--target", default=None, help="Destination directory (default: ~/.claude/skills/srp)")

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

    return parser


def _emit(data: object, fmt: str) -> None:
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


def _dispatch(args: argparse.Namespace) -> int:
    data_dir = resolve_data_dir(args.data_dir)

    if args.command == "update-topics":
        if args.add:
            values = _parse_quoted_list(args.add)
            topics_cmd.add_topics(data_dir, values, force=args.force)
        elif args.remove:
            values = _parse_quoted_list(args.remove)
            topics_cmd.remove_topics(data_dir, values)
        elif args.rename:
            old, pos = _take_quoted(args.rename, 0)
            if args.rename[pos : pos + 2] != "->":
                raise ValidationError("rename expects old->new")
            new, _ = _take_quoted(args.rename, pos + 2)
            topics_cmd.rename_topic(data_dir, old, new)
        _emit({"ok": True}, args.output)
        return 0

    if args.command == "show-topics":
        topics = topics_cmd.show_topics(data_dir)
        _emit({"topics": topics}, args.output)
        return 0

    if args.command == "update-purposes":
        if args.add:
            name, pos = _take_quoted(args.add, 0)
            if args.add[pos : pos + 1] != "=":
                raise ValidationError('add expects "name"="method"')
            method, _ = _take_quoted(args.add, pos + 1)
            purposes_cmd.add_purpose(data_dir, name=name, method=method, force=args.force)
        elif args.remove:
            purposes_cmd.remove_purposes(data_dir, _parse_quoted_list(args.remove))
        elif args.rename:
            old, pos = _take_quoted(args.rename, 0)
            if args.rename[pos : pos + 2] != "->":
                raise ValidationError("rename expects old->new")
            new, _ = _take_quoted(args.rename, pos + 2)
            purposes_cmd.rename_purpose(data_dir, old, new)
        _emit({"ok": True}, args.output)
        return 0

    if args.command == "show-purposes":
        _emit({"purposes": purposes_cmd.show_purposes(data_dir)}, args.output)
        return 0

    if args.command == "suggest-topics":
        drafts = suggestions_cmd.suggest_topics(data_dir, count=args.count)
        suggestions_cmd.stage_suggestions(data_dir, topic_candidates=drafts, purpose_candidates=[])
        _emit({"staged_topic_suggestions": drafts}, args.output)
        return 0

    if args.command == "suggest-purposes":
        drafts = suggestions_cmd.suggest_purposes(data_dir, count=args.count)
        suggestions_cmd.stage_suggestions(data_dir, topic_candidates=[], purpose_candidates=drafts)
        _emit({"staged_purpose_suggestions": drafts}, args.output)
        return 0

    if args.command == "show-pending":
        _emit(suggestions_cmd.show_pending(data_dir), args.output)
        return 0

    if args.command == "apply-pending":
        topic_sel = _id_selector(args.topics)
        purpose_sel = _id_selector(args.purposes)
        suggestions_cmd.apply_pending(data_dir, topic_ids=topic_sel, purpose_ids=purpose_sel)
        _emit({"ok": True}, args.output)
        return 0

    if args.command == "discard-pending":
        topic_sel = _id_selector(args.topics)
        purpose_sel = _id_selector(args.purposes)
        suggestions_cmd.discard_pending(data_dir, topic_ids=topic_sel, purpose_ids=purpose_sel)
        _emit({"ok": True}, args.output)
        return 0

    if args.command == "stage-suggestions":
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

    if args.command == "run-research":
        from social_research_probe.commands.parse import parse
        from social_research_probe.pipeline import run_research
        raw = f"run-research platform:{args.platform} " + " ".join(args.dsl)
        run_research(parse(raw), data_dir, args.mode)
        return 0

    if args.command == "install-skill":
        import shutil
        import subprocess
        from pathlib import Path
        src = Path(__file__).parent / "skill"
        dest = Path(args.target) if args.target else Path.home() / ".claude" / "skills" / "srp"
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(src, dest)
        print(f"Skill installed to {dest}")
        pkg = "git+https://github.com/reshinto/social-research-probe"
        if shutil.which("uv"):
            subprocess.run(["uv", "tool", "install", "--reinstall", pkg], check=True)
            print("srp CLI installed via uv tool")
        elif shutil.which("pipx"):
            subprocess.run(["pipx", "install", "--force", pkg], check=True)
            print("srp CLI installed via pipx")
        else:
            print("warning: neither uv nor pipx found — srp CLI not permanently installed")
            print(f"  run: pipx install \"{pkg}\"")
        return 0

    if args.command == "config":
        return _dispatch_config(args, data_dir)

    return 2


def _id_selector(raw: str):
    if not raw:
        return []
    if raw == "all":
        return "all"
    try:
        return [int(x.strip()) for x in raw.split(",") if x.strip()]
    except ValueError as exc:
        raise ValidationError(f"invalid id selector: {raw!r}") from exc


def _dispatch_config(args: argparse.Namespace, data_dir: Path) -> int:
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
        if args.from_stdin:
            value = sys.stdin.read().rstrip("\n")
        else:
            import getpass
            value = getpass.getpass(f"{args.name}: ")
        if not value:
            raise ValidationError("empty secret value")
        config_cmd.write_secret(data_dir, args.name, value)
        return 0
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


def main(argv: list[str] | None = None) -> int:
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


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
