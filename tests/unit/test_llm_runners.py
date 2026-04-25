"""Tests for LLM runner argv builders and JSON parsers.

Live subprocess calls are covered by monkeypatching subprocess_runner.run
so that no real subprocess is spawned during testing.

For each of the four runners (claude, gemini, codex, local) this module tests:
- health_check() when the binary is found / missing
- _build_argv() with and without a schema
- _parse_response() with valid and invalid JSON

The local runner has additional health_check tests for the env-var-missing
and path-nonexistent cases.

Who calls it: pytest, run as part of the unit test suite.
"""

from __future__ import annotations

import pytest
import social_research_probe.llm.registry as registry_module
from social_research_probe.errors import AdapterError

# Import the runner classes directly so tests do not depend on the registry.
from social_research_probe.llm.runners.claude import ClaudeRunner
from social_research_probe.llm.runners.codex import CodexRunner
from social_research_probe.llm.runners.gemini import GeminiRunner
from social_research_probe.llm.runners.local import LocalRunner
from social_research_probe.technologies.llms.claude_cli import ClaudeCliFlag
from social_research_probe.technologies.llms.codex_cli import CodexCliFlag
from social_research_probe.technologies.llms.gemini_cli import GeminiCliFlag


@pytest.fixture(autouse=True)
def _isolated_registry():
    """Save and restore _REGISTRY around every test.

    Why: importing runner modules registers them as a side effect. Tests that
    manipulate the registry must not affect each other.
    """
    original = dict(registry_module._REGISTRY)
    yield
    registry_module._REGISTRY.clear()
    registry_module._REGISTRY.update(original)


@pytest.fixture(autouse=True)
def _isolate_runner_config(monkeypatch: pytest.MonkeyPatch):
    """Keep runner argv construction independent from any real home config."""
    import social_research_probe.llm.runners.cli_json_base as base_mod

    class _FakeConfig:
        llm_timeout_seconds = 30

        def llm_settings(self, name: str) -> dict[str, object]:
            return {}

    monkeypatch.setattr(base_mod, "load_active_config", lambda: _FakeConfig())


# ---------------------------------------------------------------------------
# ClaudeRunner
# ---------------------------------------------------------------------------


def test_claude_health_check_true_when_binary_found(monkeypatch: pytest.MonkeyPatch) -> None:
    """health_check returns True when shutil.which finds the claude binary.

    Monkeypatches shutil.which in the claude module so no real binary is needed.
    """
    import social_research_probe.llm.runners.cli_json_base as base_mod

    monkeypatch.setattr(base_mod.shutil, "which", lambda name: "/usr/local/bin/claude")
    runner = ClaudeRunner()
    assert runner.health_check() is True


def test_claude_health_check_false_when_binary_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """health_check returns False when shutil.which cannot find the claude binary."""
    import social_research_probe.llm.runners.cli_json_base as base_mod

    monkeypatch.setattr(base_mod.shutil, "which", lambda name: None)
    runner = ClaudeRunner()
    assert runner.health_check() is False


def test_claude_build_argv_no_schema() -> None:
    """_build_argv without a schema returns the base claude invocation only."""
    runner = ClaudeRunner()
    argv = runner._build_argv(schema=None)
    assert argv == ["claude", ClaudeCliFlag.PRINT, ClaudeCliFlag.OUTPUT_FORMAT, "json"]
    assert ClaudeCliFlag.JSON_SCHEMA not in argv


def test_claude_build_argv_with_schema() -> None:
    """_build_argv with a schema appends Claude's JSON-schema flag."""
    import json

    runner = ClaudeRunner()
    schema = {"type": "object", "properties": {"result": {"type": "string"}}}
    argv = runner._build_argv(schema=schema)
    assert ClaudeCliFlag.JSON_SCHEMA in argv
    idx = argv.index(ClaudeCliFlag.JSON_SCHEMA)
    assert json.loads(argv[idx + 1]) == schema


def test_claude_parse_response_valid_json() -> None:
    """_parse_response returns a dict when stdout is valid JSON."""
    runner = ClaudeRunner()
    result = runner._parse_response('{"key": "value"}')
    assert result == {"key": "value"}


def test_claude_parse_response_invalid_json_raises_adapter_error() -> None:
    """_parse_response raises AdapterError when stdout is not valid JSON."""
    runner = ClaudeRunner()
    with pytest.raises(AdapterError, match="claude returned non-JSON"):
        runner._parse_response("this is not json")


# ---------------------------------------------------------------------------
# GeminiRunner
# ---------------------------------------------------------------------------


def test_gemini_health_check_true_when_binary_found(monkeypatch: pytest.MonkeyPatch) -> None:
    """health_check returns True when shutil.which finds the gemini binary."""
    import social_research_probe.llm.runners.cli_json_base as base_mod

    monkeypatch.setattr(base_mod.shutil, "which", lambda name: "/usr/local/bin/gemini")
    runner = GeminiRunner()
    assert runner.health_check() is True


def test_gemini_health_check_false_when_binary_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """health_check returns False when shutil.which cannot find the gemini binary."""
    import social_research_probe.llm.runners.cli_json_base as base_mod

    monkeypatch.setattr(base_mod.shutil, "which", lambda name: None)
    runner = GeminiRunner()
    assert runner.health_check() is False


def test_gemini_build_argv_no_schema() -> None:
    """_build_argv without a schema returns the base gemini invocation only."""
    runner = GeminiRunner()
    argv = runner._build_argv(schema=None)
    assert argv == ["gemini", GeminiCliFlag.OUTPUT_FORMAT, "json"]
    assert "--schema" not in argv


def test_gemini_build_argv_with_schema() -> None:
    """Gemini ignores schema at argv-build time because it lacks inline schema support."""
    runner = GeminiRunner()
    schema = {"type": "object"}
    argv = runner._build_argv(schema=schema)
    assert argv == ["gemini", GeminiCliFlag.OUTPUT_FORMAT, "json"]
    assert "--schema" not in argv


def test_gemini_parse_response_valid_json() -> None:
    """_parse_response unwraps the gemini CLI envelope and parses the inner JSON."""
    runner = GeminiRunner()
    envelope = '{"session_id": "x", "response": "{\\"key\\": \\"value\\"}", "stats": {}}'
    result = runner._parse_response(envelope)
    assert result == {"key": "value"}


def test_gemini_parse_response_markdown_fenced_json() -> None:
    """_parse_response strips markdown fences before parsing the inner JSON."""
    runner = GeminiRunner()
    inner = '```json\n{"key": "value"}\n```'
    import json as _json

    envelope = _json.dumps({"response": inner})
    result = runner._parse_response(envelope)
    assert result == {"key": "value"}


def test_gemini_parse_response_invalid_json_raises_adapter_error() -> None:
    """_parse_response raises AdapterError when stdout is not valid JSON."""
    runner = GeminiRunner()
    with pytest.raises(AdapterError, match="gemini returned non-JSON"):
        runner._parse_response("not json at all")


# ---------------------------------------------------------------------------
# CodexRunner
# ---------------------------------------------------------------------------


def test_codex_health_check_true_when_binary_found(monkeypatch: pytest.MonkeyPatch) -> None:
    """health_check returns True when shutil.which finds the codex binary."""
    import social_research_probe.llm.runners.cli_json_base as base_mod

    monkeypatch.setattr(base_mod.shutil, "which", lambda name: "/usr/local/bin/codex")
    runner = CodexRunner()
    assert runner.health_check() is True


def test_codex_health_check_false_when_binary_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """health_check returns False when shutil.which cannot find the codex binary."""
    import social_research_probe.llm.runners.cli_json_base as base_mod

    monkeypatch.setattr(base_mod.shutil, "which", lambda name: None)
    runner = CodexRunner()
    assert runner.health_check() is False


def test_codex_build_argv_no_schema() -> None:
    """_build_argv without a schema returns the base codex invocation only."""
    runner = CodexRunner()
    argv = runner._build_argv(schema=None)
    assert argv == ["codex", "exec"]
    assert "--schema" not in argv


def test_codex_build_argv_with_schema() -> None:
    """Codex handles schema via temp files during run(), not inline argv."""
    runner = CodexRunner()
    schema = {"type": "object"}
    argv = runner._build_argv(schema=schema)
    assert argv == ["codex", "exec"]
    assert "--schema" not in argv


def test_codex_parse_response_valid_json() -> None:
    """_parse_response returns a dict when stdout is valid JSON."""
    runner = CodexRunner()
    result = runner._parse_response('{"answer": 42}')
    assert result == {"answer": 42}


def test_codex_parse_response_invalid_json_raises_adapter_error() -> None:
    """_parse_response raises AdapterError when stdout is not valid JSON."""
    runner = CodexRunner()
    with pytest.raises(AdapterError, match="codex returned non-JSON"):
        runner._parse_response("{broken json")


# ---------------------------------------------------------------------------
# LocalRunner
# ---------------------------------------------------------------------------


def test_local_health_check_true_when_binary_found(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """health_check returns True when SRP_LOCAL_LLM_BIN points to an existing file."""
    bin_file = tmp_path / "my_llm"
    bin_file.write_text("#!/bin/sh\n")
    monkeypatch.setenv("SRP_LOCAL_LLM_BIN", str(bin_file))
    runner = LocalRunner()
    assert runner.health_check() is True


def test_local_health_check_false_when_binary_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """health_check returns False when SRP_LOCAL_LLM_BIN points to a non-existent path."""
    monkeypatch.setenv("SRP_LOCAL_LLM_BIN", str(tmp_path / "does_not_exist"))
    runner = LocalRunner()
    assert runner.health_check() is False


def test_local_health_check_false_when_env_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """health_check returns False when SRP_LOCAL_LLM_BIN is not set at all.

    Without the env var the runner is not configured, so it should report
    unavailability rather than raising an exception.
    """
    monkeypatch.delenv("SRP_LOCAL_LLM_BIN", raising=False)
    runner = LocalRunner()
    assert runner.health_check() is False


def test_local_health_check_false_when_path_nonexistent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """health_check returns False when SRP_LOCAL_LLM_BIN is set but path does not exist.

    Why test separately from binary_missing: ensures the os.path.exists check
    is exercised even when the env var itself is present.
    """
    monkeypatch.setenv("SRP_LOCAL_LLM_BIN", "/absolutely/nonexistent/path/llm")
    runner = LocalRunner()
    assert runner.health_check() is False


def test_local_build_argv_no_schema(monkeypatch: pytest.MonkeyPatch) -> None:
    """_build_argv without a schema returns just the binary path."""
    monkeypatch.setenv("SRP_LOCAL_LLM_BIN", "/opt/llm/bin/model")
    runner = LocalRunner()
    argv = runner._build_argv(schema=None)
    assert argv == ["/opt/llm/bin/model"]
    assert "--schema" not in argv


def test_local_build_argv_with_schema(monkeypatch: pytest.MonkeyPatch) -> None:
    """_build_argv with a schema appends --schema and the JSON-encoded schema."""
    import json

    monkeypatch.setenv("SRP_LOCAL_LLM_BIN", "/opt/llm/bin/model")
    runner = LocalRunner()
    schema = {"type": "object"}
    argv = runner._build_argv(schema=schema)
    assert argv[0] == "/opt/llm/bin/model"
    assert "--schema" in argv
    idx = argv.index("--schema")
    assert json.loads(argv[idx + 1]) == schema


def test_local_parse_response_valid_json() -> None:
    """_parse_response returns a dict when stdout is valid JSON."""
    runner = LocalRunner()
    result = runner._parse_response('{"result": "ok"}')
    assert result == {"result": "ok"}


def test_local_parse_response_invalid_json_raises_adapter_error() -> None:
    """_parse_response raises AdapterError when stdout is not valid JSON."""
    runner = LocalRunner()
    with pytest.raises(AdapterError, match="local LLM returned non-JSON"):
        runner._parse_response("definitely not json")


# ---------------------------------------------------------------------------
# run() integration — monkeypatched subprocess_runner
# ---------------------------------------------------------------------------


def _make_completed(stdout: str):
    """Return a minimal subprocess.CompletedProcess stand-in."""
    import subprocess

    return subprocess.CompletedProcess(args=[], returncode=0, stdout=stdout, stderr="")


def test_claude_run_monkeypatched(monkeypatch: pytest.MonkeyPatch) -> None:
    """run() calls subprocess_runner.run and parses JSON from stdout."""
    import social_research_probe.utils.subprocess_runner as sp_mod

    monkeypatch.setattr(
        sp_mod, "run", lambda argv, input=None, timeout=30: _make_completed('{"ok": 1}')
    )
    runner = ClaudeRunner()
    assert runner.run("hello") == {"ok": 1}


def test_gemini_run_monkeypatched(monkeypatch: pytest.MonkeyPatch) -> None:
    """run() calls subprocess_runner.run, unwraps the gemini envelope, and parses inner JSON."""
    import json as _json

    import social_research_probe.utils.subprocess_runner as sp_mod

    envelope = _json.dumps({"session_id": "s", "response": '{"ok": 2}', "stats": {}})
    monkeypatch.setattr(
        sp_mod, "run", lambda argv, input=None, timeout=30: _make_completed(envelope)
    )
    runner = GeminiRunner()
    assert runner.run("hello") == {"ok": 2}


def test_gemini_run_uses_configured_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    """Structured runners use llm.timeout_seconds from config."""
    import social_research_probe.llm.runners.cli_json_base as base_mod
    import social_research_probe.utils.subprocess_runner as sp_mod

    class _Cfg:
        llm_timeout_seconds = 77

        def llm_settings(self, name: str) -> dict[str, object]:
            return {}

    captured = {}

    import json as _json

    envelope = _json.dumps({"session_id": "s", "response": '{"ok": 2}', "stats": {}})

    def fake_run(argv, input=None, timeout=30):
        captured["timeout"] = timeout
        return _make_completed(envelope)

    monkeypatch.setattr(base_mod, "load_active_config", lambda: _Cfg())
    monkeypatch.setattr(sp_mod, "run", fake_run)
    runner = GeminiRunner()
    assert runner.run("hello") == {"ok": 2}
    assert captured["timeout"] == 77


def test_codex_run_monkeypatched(monkeypatch: pytest.MonkeyPatch) -> None:
    """run() calls subprocess_runner.run and parses JSON from stdout."""
    import social_research_probe.utils.subprocess_runner as sp_mod

    monkeypatch.setattr(
        sp_mod, "run", lambda argv, input=None, timeout=30: _make_completed('{"ok": 3}')
    )
    runner = CodexRunner()
    assert runner.run("hello") == {"ok": 3}


def test_local_run_monkeypatched(monkeypatch: pytest.MonkeyPatch) -> None:
    """run() calls subprocess_runner.run and parses JSON from stdout."""
    import social_research_probe.utils.subprocess_runner as sp_mod

    monkeypatch.setattr(
        sp_mod, "run", lambda argv, input=None, timeout=30: _make_completed('{"ok": 4}')
    )
    monkeypatch.setenv("SRP_LOCAL_LLM_BIN", "/fake/llm")
    runner = LocalRunner()
    assert runner.run("hello") == {"ok": 4}


# ---------------------------------------------------------------------------
# Base class _prompt_args and _stdin_input default implementations
# ---------------------------------------------------------------------------


class _MinimalRunner(
    __import__(
        "social_research_probe.llm.runners.cli_json_base", fromlist=["JsonCliRunner"]
    ).JsonCliRunner
):
    """Minimal concrete subclass that uses the base-class prompt/stdin defaults."""

    name = "minimal"
    binary_name = "minimal"
    base_argv = ()
    schema_flag = None


def test_base_prompt_args_returns_empty_list() -> None:
    """The default _prompt_args implementation returns [] (prompt goes via stdin)."""
    runner = _MinimalRunner()
    assert runner._prompt_args("hello") == []


def test_base_stdin_input_returns_prompt() -> None:
    """The default _stdin_input implementation returns the prompt string unchanged."""
    runner = _MinimalRunner()
    assert runner._stdin_input("hello") == "hello"


# ---------------------------------------------------------------------------
# CodexRunner — schema file path and AdapterError re-raise
# ---------------------------------------------------------------------------


def test_codex_run_with_schema_writes_schema_file(monkeypatch: pytest.MonkeyPatch) -> None:
    """CodexRunner.run() with a schema writes it to a temp file and adds --output-schema."""

    captured_argv: list[str] = []

    class _FakeResult:
        returncode = 0
        stdout = '{"ok": 1}'
        stderr = ""

    def fake_run(argv, input=None, timeout=30):
        captured_argv.extend(argv)
        return _FakeResult()

    import social_research_probe.utils.subprocess_runner as sp_mod

    monkeypatch.setattr(sp_mod, "run", fake_run)
    runner = CodexRunner()
    schema = {"type": "object", "properties": {"x": {"type": "string"}}}
    result = runner.run("hello", schema=schema)
    assert result == {"ok": 1}
    assert CodexCliFlag.OUTPUT_SCHEMA in captured_argv


def test_codex_run_raises_adapter_error_when_output_json_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CodexRunner.run() re-raises AdapterError when the output file contains invalid JSON."""
    import social_research_probe.utils.subprocess_runner as sp_mod

    class _FakeResult:
        returncode = 0
        stdout = "not json"
        stderr = ""

    monkeypatch.setattr(sp_mod, "run", lambda argv, input=None, timeout=30: _FakeResult())
    runner = CodexRunner()
    with pytest.raises(AdapterError, match="codex returned non-JSON final message"):
        runner.run("hello")


# ---------------------------------------------------------------------------
# GeminiRunner — invalid inner JSON in response field
# ---------------------------------------------------------------------------


def test_gemini_parse_response_invalid_inner_json_raises_adapter_error() -> None:
    """_parse_response raises AdapterError when the 'response' field is not valid JSON."""
    import json as _json

    runner = GeminiRunner()
    envelope = _json.dumps({"response": "this is not json", "stats": {}})
    with pytest.raises(AdapterError, match="gemini response field is not valid JSON"):
        runner._parse_response(envelope)
