"""srp schedule subcommand: print local scheduling helpers."""

from __future__ import annotations

import argparse
import shlex
import shutil
import sys
from pathlib import Path
from xml.sax.saxutils import escape

from social_research_probe.utils.core.exit_codes import ExitCode

_LABEL = "local.social-research-probe.watch-run-due"


def _cron(args: argparse.Namespace) -> int:
    from social_research_probe.config import load_active_config
    from social_research_probe.utils.monitoring.schedule import cron_schedule

    cfg = load_active_config()
    interval = _selected_interval(args, cfg)
    command = shlex.join(_watch_command(cfg))
    lines = [
        "# Social Research Probe local watch schedule",
        "# Add this line with `crontab -e`; srp does not install it automatically.",
        f"{cron_schedule(interval)} {command}",
    ]
    print("\n".join(lines))
    return ExitCode.SUCCESS


def _launchd(args: argparse.Namespace) -> int:
    from social_research_probe.config import load_active_config

    cfg = load_active_config()
    plist = _launchd_plist(_watch_command(cfg), _selected_interval(args, cfg))
    output = getattr(args, "output_path", None)
    if output:
        path = Path(output).expanduser()
        path.write_text(plist, encoding="utf-8")
        print(f"Wrote launchd plist to {path}")
    else:
        print(plist)
    return ExitCode.SUCCESS


def _launchd_plist(command: list[str], interval: str) -> str:
    from social_research_probe.utils.monitoring.schedule import interval_seconds

    args_xml = "\n".join(f"    <string>{escape(arg)}</string>" for arg in command)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>{_LABEL}</string>
  <key>ProgramArguments</key>
  <array>
{args_xml}
  </array>
  <key>StartInterval</key>
  <integer>{interval_seconds(interval)}</integer>
  <key>RunAtLoad</key>
  <false/>
</dict>
</plist>
"""


def _watch_command(cfg: object) -> list[str]:
    return [
        _current_executable(),
        "--data-dir",
        str(cfg.data_dir),
        "watch",
        "run-due",
        "--notify",
    ]


def _current_executable() -> str:
    raw = sys.argv[0] or "srp"
    path = Path(raw).expanduser()
    if path.parent != Path("."):
        return str(path if path.is_absolute() else path.resolve())
    return shutil.which(raw) or raw


def _selected_interval(args: argparse.Namespace, cfg: object) -> str:
    raw = getattr(args, "interval", None) or _schedule_default(cfg)
    return raw if raw in {"hourly", "daily", "weekly"} else "daily"


def _schedule_default(cfg: object) -> str:
    raw = getattr(cfg, "raw", {})
    if isinstance(raw, dict):
        schedule = raw.get("schedule", {})
        if isinstance(schedule, dict) and isinstance(schedule.get("default_interval"), str):
            return str(schedule["default_interval"])
    return "daily"


def run(args: argparse.Namespace) -> int:
    """Dispatch schedule helper subcommands."""
    from social_research_probe.commands import ScheduleSubcommand

    if not getattr(args, "schedule_cmd", None):
        parser = getattr(args, "_schedule_parser", None)
        if parser:
            parser.print_help()
        return ExitCode.SUCCESS
    if args.schedule_cmd == ScheduleSubcommand.CRON:
        return _cron(args)
    if args.schedule_cmd == ScheduleSubcommand.LAUNCHD:
        return _launchd(args)
    return ExitCode.ERROR
