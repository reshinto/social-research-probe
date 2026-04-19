"""Unit tests for commands/research.py.

Why this file exists:
    Verifies that the research command correctly bridges CLI arguments to
    pipeline.run_research, and that it prints JSON output in cli mode without
    printing anything in skill mode (where the pipeline itself handles output).

Who calls it:
    pytest during CI and local test runs.
"""
from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from social_research_probe.commands import research as research_cmd


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FAKE_PACKET = {"topic": "AI trends", "platform": "youtube", "items_top5": []}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_run_parses_dsl_and_calls_pipeline(monkeypatch, tmp_path):
    """run() must call parse_dsl then run_research with the reconstructed DSL.

    We monkeypatch both so no real adapter or LLM is involved.
    """
    captured_raw = {}

    # Record what parse_dsl receives.
    def fake_parse(raw: str):
        captured_raw["raw"] = raw
        return object()  # sentinel — we only care it's passed through

    captured_call = {}

    # Record what run_research receives.
    def fake_run_research(cmd, data_dir, mode):
        captured_call["cmd"] = cmd
        captured_call["data_dir"] = data_dir
        captured_call["mode"] = mode
        return _FAKE_PACKET

    monkeypatch.setattr(research_cmd, "parse_dsl", fake_parse)
    monkeypatch.setattr(research_cmd, "run_research", fake_run_research)

    research_cmd.run(
        platform="youtube",
        dsl_args=['"ai trends"->latest-news'],
        data_dir=tmp_path,
        mode="cli",
    )

    # The DSL string must start with the run-research prefix and contain the platform.
    assert captured_raw["raw"].startswith("run-research platform:youtube")
    assert '"ai trends"->latest-news' in captured_raw["raw"]
    assert captured_call["data_dir"] == tmp_path
    assert captured_call["mode"] == "cli"


def test_run_cli_mode_prints_json(monkeypatch, tmp_path, capsys):
    """In cli mode, run() must write the packet as indented JSON to stdout."""
    monkeypatch.setattr(research_cmd, "parse_dsl", lambda raw: object())
    monkeypatch.setattr(research_cmd, "run_research", lambda cmd, d, m: _FAKE_PACKET)

    rc = research_cmd.run(
        platform="youtube",
        dsl_args=["dsl-arg"],
        data_dir=tmp_path,
        mode="cli",
    )

    assert rc == 0
    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert parsed["topic"] == "AI trends"
    assert parsed["platform"] == "youtube"


def test_run_skill_mode_does_not_print(monkeypatch, tmp_path, capsys):
    """In skill mode, run() must not print anything (pipeline handles output).

    run_research is called with mode='skill'. The function returns 0 and
    stdout stays empty.
    """
    skill_calls = []

    def fake_run_research(cmd, data_dir, mode):
        skill_calls.append(mode)
        # In real skill mode the pipeline exits via llm/host.py; we just return.
        return _FAKE_PACKET

    monkeypatch.setattr(research_cmd, "parse_dsl", lambda raw: object())
    monkeypatch.setattr(research_cmd, "run_research", fake_run_research)

    rc = research_cmd.run(
        platform="youtube",
        dsl_args=["dsl-arg"],
        data_dir=tmp_path,
        mode="skill",
    )

    assert rc == 0
    assert skill_calls == ["skill"]
    captured = capsys.readouterr()
    # skill mode must NOT produce output from this wrapper
    assert captured.out == ""
