"""End-to-end research CLI tests with deterministic fake providers.

from social_research_probe.commands import Command, ConfigSubcommand

These tests shell out through the real ``python -m social_research_probe.cli``
entrypoint, but replace external dependencies with local fakes:

- Fake YouTube adapter via ``SRP_TEST_USE_FAKE_YOUTUBE=1``
- Fake corroboration backends via ``SRP_TEST_USE_FAKE_CORROBORATION=1``
- Fake Gemini / Claude / Codex runner binaries on PATH

This keeps the coverage genuinely integration-level while remaining offline
and deterministic.
"""

from __future__ import annotations

import os
import shlex
import stat
import subprocess
import sys
from pathlib import Path

from social_research_probe.cli.parsers import Arg
from social_research_probe.commands import Command, ConfigSubcommand

REPO_ROOT = Path(__file__).resolve().parents[2]
_SUMMARY_PHRASE = "Generated summary from codex fallback."
_EXPECTED_COMPILED_SYNTHESIS = "Compiled synthesis from codex fallback."
_EXPECTED_OPPORTUNITY_ANALYSIS = "Opportunity analysis from codex fallback."
_EXPECTED_REPORT_SUMMARY = "Final report summary from codex fallback."


def _run(
    data_dir: Path,
    env: dict[str, str],
    *args: str,
    stdin: str | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "social_research_probe.cli", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        input=stdin,
        env=env,
    )


def _write_executable(path: Path, source: str) -> None:
    path.write_text(source, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _install_fake_runner_binaries(bin_dir: Path) -> None:
    python = sys.executable

    failing_cli = f"""#!{python}
import sys
sys.stderr.write("simulated failure\\n")
sys.exit(1)
"""
    _write_executable(bin_dir / "gemini", failing_cli)
    _write_executable(bin_dir / "claude", failing_cli)

    summary_tail = " ".join(f"detail{i}" for i in range(1, 230))
    codex_cli = f"""#!{python}
import json
import sys
from pathlib import Path
from social_research_probe.cli.parsers import Arg

SUMMARY = "{_SUMMARY_PHRASE} {summary_tail}"
SYNTHESIS = {{
    "compiled_synthesis": "{_EXPECTED_COMPILED_SYNTHESIS}",
    "opportunity_analysis": "{_EXPECTED_OPPORTUNITY_ANALYSIS}",
    "report_summary": "{_EXPECTED_REPORT_SUMMARY}",
}}

args = sys.argv[1:]
if not args or args[0] != "exec":
    sys.stderr.write("expected codex exec\\n")
    sys.exit(2)
args = args[1:]
output_path = None
i = 0
while i < len(args) and args[i].startswith("--"):
    flag = args[i]
    if flag in ("--output-last-message", "--output-schema"):
        if i + 1 >= len(args):
            sys.stderr.write(f"missing value for {{flag}}\\n")
            sys.exit(2)
        if flag == "--output-last-message":
            output_path = Path(args[i + 1])
        i += 2
        continue
    sys.stderr.write(f"unexpected flag: {{flag}}\\n")
    sys.exit(2)

if output_path is not None:
    output_path.write_text(json.dumps(SYNTHESIS), encoding="utf-8")
else:
    sys.stdout.write(SUMMARY)
"""
    _write_executable(bin_dir / "codex", codex_cli)


def _test_env(data_dir: Path, bin_dir: Path) -> dict[str, str]:
    pythonpath_parts = [str(REPO_ROOT)]
    existing_pythonpath = os.environ.get("PYTHONPATH")
    if existing_pythonpath:
        pythonpath_parts.append(existing_pythonpath)
    return {
        **os.environ,
        "SRP_DATA_DIR": str(data_dir),
        "SRP_TEST_USE_FAKE_YOUTUBE": "1",
        "SRP_TEST_USE_FAKE_CORROBORATION": "1",
        "PYTHONPATH": os.pathsep.join(pythonpath_parts),
        "PATH": os.pathsep.join([str(bin_dir), os.environ.get("PATH", "")]),
    }


def _configure_research_stack(data_dir: Path, env: dict[str, str]) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)

    commands = [
        (Command.UPDATE_PURPOSES, Arg.ADD, '"trends"="Track emergence across channels"'),
        (Command.CONFIG, ConfigSubcommand.SET, "llm.runner", "gemini"),
        (Command.CONFIG, ConfigSubcommand.SET, "technologies.gemini", "true"),
        (Command.CONFIG, ConfigSubcommand.SET, "technologies.codex", "true"),
        (Command.CONFIG, ConfigSubcommand.SET, "corroboration.backend", "auto"),
    ]
    for args in commands:
        result = _run(data_dir, env, *args)
        assert result.returncode == 0, result.stderr

    for secret_name, secret_value in (
        ("exa_api_key", "exa-test-key"),
        ("tavily_api_key", "tavily-test-key"),
    ):
        result = _run(
            data_dir,
            env,
            "config",
            ConfigSubcommand.SET_SECRET,
            secret_name,
            Arg.FROM_STDIN,
            stdin=secret_value,
        )
        assert result.returncode == 0, result.stderr


def _path_from_serve_report_command(command: str) -> Path:
    parts = shlex.split(command)
    assert parts[:3] == ["srp", "serve-report", Arg.REPORT], command
    return Path(parts[3]).expanduser()


def test_research_packet_and_html_end_to_end(tmp_path: Path) -> None:
    data_dir = tmp_path / ".skill-data"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _install_fake_runner_binaries(bin_dir)
    env = _test_env(data_dir, bin_dir)
    _configure_research_stack(data_dir, env)

    result = _run(data_dir, env, "research", "youtube", "ai agents", "trends")
    assert result.returncode == 0, result.stderr
    stdout_command = result.stdout.strip()
    assert stdout_command.startswith("srp serve-report --report ")

    report_path = _path_from_serve_report_command(stdout_command)
    assert report_path.exists()
    html = report_path.read_text(encoding="utf-8")
    assert _SUMMARY_PHRASE in html

    if _EXPECTED_COMPILED_SYNTHESIS not in html:
        print("STDERR:", result.stderr)
        print("STDOUT:", result.stdout)
        raise AssertionError("_EXPECTED_COMPILED_SYNTHESIS not found in html")

    assert _EXPECTED_OPPORTUNITY_ANALYSIS in html
    assert _EXPECTED_REPORT_SUMMARY in html
    assert "_(LLM synthesis unavailable" not in html
    assert "_(LLM summary unavailable" not in html
    assert "source corroboration was not run; trust scores are heuristic only" not in html
    assert _SUMMARY_PHRASE in html
    assert "<th>Model</th>" in html
    assert "<th>What it means</th>" in html
