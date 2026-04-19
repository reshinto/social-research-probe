"""Tests for LLM runner argv builders and JSON parsers.

Live subprocess calls are excluded from coverage (marked with
# pragma: no cover — live subprocess on the run() methods themselves).

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


# ---------------------------------------------------------------------------
# ClaudeRunner
# ---------------------------------------------------------------------------


def test_claude_health_check_true_when_binary_found(monkeypatch: pytest.MonkeyPatch) -> None:
    """health_check returns True when shutil.which finds the claude binary.

    Monkeypatches shutil.which in the claude module so no real binary is needed.
    """
    import social_research_probe.llm.runners.claude as claude_mod

    monkeypatch.setattr(claude_mod.shutil, "which", lambda name: "/usr/local/bin/claude")
    runner = ClaudeRunner()
    assert runner.health_check() is True


def test_claude_health_check_false_when_binary_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """health_check returns False when shutil.which cannot find the claude binary."""
    import social_research_probe.llm.runners.claude as claude_mod

    monkeypatch.setattr(claude_mod.shutil, "which", lambda name: None)
    runner = ClaudeRunner()
    assert runner.health_check() is False


def test_claude_build_argv_no_schema() -> None:
    """_build_argv without a schema returns the base claude invocation only."""
    runner = ClaudeRunner()
    argv = runner._build_argv(schema=None)
    assert argv == ["claude", "--output-format", "json"]
    # --schema flag must not appear when no schema is supplied.
    assert "--schema" not in argv


def test_claude_build_argv_with_schema() -> None:
    """_build_argv with a schema appends --schema and the JSON-encoded schema."""
    import json

    runner = ClaudeRunner()
    schema = {"type": "object", "properties": {"result": {"type": "string"}}}
    argv = runner._build_argv(schema=schema)
    assert "--schema" in argv
    # The value immediately after --schema must be the JSON encoding of the schema.
    idx = argv.index("--schema")
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
    import social_research_probe.llm.runners.gemini as gemini_mod

    monkeypatch.setattr(gemini_mod.shutil, "which", lambda name: "/usr/local/bin/gemini")
    runner = GeminiRunner()
    assert runner.health_check() is True


def test_gemini_health_check_false_when_binary_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """health_check returns False when shutil.which cannot find the gemini binary."""
    import social_research_probe.llm.runners.gemini as gemini_mod

    monkeypatch.setattr(gemini_mod.shutil, "which", lambda name: None)
    runner = GeminiRunner()
    assert runner.health_check() is False


def test_gemini_build_argv_no_schema() -> None:
    """_build_argv without a schema returns the base gemini invocation only."""
    runner = GeminiRunner()
    argv = runner._build_argv(schema=None)
    assert argv == ["gemini", "--format", "json"]
    assert "--schema" not in argv


def test_gemini_build_argv_with_schema() -> None:
    """_build_argv with a schema appends --schema and the JSON-encoded schema."""
    import json

    runner = GeminiRunner()
    schema = {"type": "object"}
    argv = runner._build_argv(schema=schema)
    assert "--schema" in argv
    idx = argv.index("--schema")
    assert json.loads(argv[idx + 1]) == schema


def test_gemini_parse_response_valid_json() -> None:
    """_parse_response returns a dict when stdout is valid JSON."""
    runner = GeminiRunner()
    result = runner._parse_response('{"key": "value"}')
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
    import social_research_probe.llm.runners.codex as codex_mod

    monkeypatch.setattr(codex_mod.shutil, "which", lambda name: "/usr/local/bin/codex")
    runner = CodexRunner()
    assert runner.health_check() is True


def test_codex_health_check_false_when_binary_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """health_check returns False when shutil.which cannot find the codex binary."""
    import social_research_probe.llm.runners.codex as codex_mod

    monkeypatch.setattr(codex_mod.shutil, "which", lambda name: None)
    runner = CodexRunner()
    assert runner.health_check() is False


def test_codex_build_argv_no_schema() -> None:
    """_build_argv without a schema returns the base codex invocation only."""
    runner = CodexRunner()
    argv = runner._build_argv(schema=None)
    assert argv == ["codex", "--json"]
    assert "--schema" not in argv


def test_codex_build_argv_with_schema() -> None:
    """_build_argv with a schema appends --schema and the JSON-encoded schema."""
    import json

    runner = CodexRunner()
    schema = {"type": "object"}
    argv = runner._build_argv(schema=schema)
    assert "--schema" in argv
    idx = argv.index("--schema")
    assert json.loads(argv[idx + 1]) == schema


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
