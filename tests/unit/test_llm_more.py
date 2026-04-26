"""Cover claude_cli.agentic_search, gemini summarize_media, codex.run paths."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from social_research_probe.technologies.llms import gemini_cli
from social_research_probe.technologies.llms.claude_cli import ClaudeRunner
from social_research_probe.technologies.llms.codex_cli import CodexRunner
from social_research_probe.technologies.llms.gemini_cli import GeminiRunner
from social_research_probe.utils.core.errors import AdapterError


class TestClaudeAgenticSearch:
    """Bypass prompt formatting bug by patching CLAUDE_SEARCH_PROMPT to a safe template."""

    @pytest.fixture(autouse=True)
    def _patch_prompt(self, monkeypatch):
        monkeypatch.setattr(
            "social_research_probe.technologies.llms.claude_cli.CLAUDE_SEARCH_PROMPT",
            "search {query}",
        )

    def test_failure_raises(self, monkeypatch):
        cfg = MagicMock()
        cfg.llm_settings.return_value = {"binary": "claude"}
        with (
            patch(
                "social_research_probe.technologies.llms.load_active_config",
                return_value=cfg,
            ),
            patch(
                "social_research_probe.technologies.llms.claude_cli.sp_run",
                side_effect=OSError("boom"),
            ),
            pytest.raises(AdapterError),
        ):
            asyncio.run(ClaudeRunner().agentic_search("q"))

    def test_success(self, monkeypatch):
        cfg = MagicMock()
        cfg.llm_settings.return_value = {"binary": "claude"}
        result = MagicMock(
            stdout=json.dumps({"result": json.dumps({"answer": "a", "citations": []})})
        )
        with (
            patch(
                "social_research_probe.technologies.llms.load_active_config",
                return_value=cfg,
            ),
            patch(
                "social_research_probe.technologies.llms.claude_cli.sp_run",
                return_value=result,
            ),
        ):
            out = asyncio.run(ClaudeRunner().agentic_search("q"))
        assert out.runner_name == "claude"

    def test_non_string_inner(self, monkeypatch):
        cfg = MagicMock()
        cfg.llm_settings.return_value = {"binary": "claude"}
        result = MagicMock(stdout=json.dumps({"result": 5}))
        with (
            patch(
                "social_research_probe.technologies.llms.load_active_config",
                return_value=cfg,
            ),
            patch(
                "social_research_probe.technologies.llms.claude_cli.sp_run",
                return_value=result,
            ),
        ):
            out = asyncio.run(ClaudeRunner().agentic_search("q"))
        assert out.answer == ""

    def test_envelope_not_dict(self, monkeypatch):
        cfg = MagicMock()
        cfg.llm_settings.return_value = {"binary": "claude"}
        result = MagicMock(stdout=json.dumps([1, 2]))
        with (
            patch(
                "social_research_probe.technologies.llms.load_active_config",
                return_value=cfg,
            ),
            patch(
                "social_research_probe.technologies.llms.claude_cli.sp_run",
                return_value=result,
            ),
        ):
            out = asyncio.run(ClaudeRunner().agentic_search("q"))
        assert out.answer == ""


class TestGeminiSummarizeMedia:
    def test_success(self, monkeypatch):
        cfg = MagicMock()
        cfg.llm_settings.return_value = {"binary": "gemini"}
        monkeypatch.setattr(GeminiRunner, "health_check", lambda self: True)
        monkeypatch.setattr(gemini_cli.shutil, "which", lambda b: "/x")
        result = MagicMock(stdout=json.dumps({"response": "summary"}))
        with (
            patch(
                "social_research_probe.technologies.llms.load_active_config",
                return_value=cfg,
            ),
            patch(
                "social_research_probe.technologies.llms.gemini_cli.subprocess_run",
                return_value=result,
            ),
        ):
            out = asyncio.run(GeminiRunner().summarize_media("https://x"))
        assert out == "summary"

    def test_non_string_response(self, monkeypatch):
        cfg = MagicMock()
        cfg.llm_settings.return_value = {"binary": "gemini"}
        monkeypatch.setattr(GeminiRunner, "health_check", lambda self: True)
        result = MagicMock(stdout=json.dumps({"response": 5}))
        with (
            patch(
                "social_research_probe.technologies.llms.load_active_config",
                return_value=cfg,
            ),
            patch(
                "social_research_probe.technologies.llms.gemini_cli.subprocess_run",
                return_value=result,
            ),
        ):
            out = asyncio.run(GeminiRunner().summarize_media("https://x"))
        assert out is None

    def test_empty_strip_returns_none(self, monkeypatch):
        cfg = MagicMock()
        cfg.llm_settings.return_value = {"binary": "gemini"}
        monkeypatch.setattr(GeminiRunner, "health_check", lambda self: True)
        result = MagicMock(stdout=json.dumps({"response": "   "}))
        with (
            patch(
                "social_research_probe.technologies.llms.load_active_config",
                return_value=cfg,
            ),
            patch(
                "social_research_probe.technologies.llms.gemini_cli.subprocess_run",
                return_value=result,
            ),
        ):
            out = asyncio.run(GeminiRunner().summarize_media("https://x"))
        assert out is None


class TestCodexRun:
    def test_run_with_schema_writes_file(self, monkeypatch, tmp_path):
        cfg = MagicMock()
        cfg.llm_settings.return_value = {"binary": "codex"}
        cfg.llm_timeout_seconds = 10
        captured_argv = []

        def fake_sp_run(argv, **kw):
            captured_argv.append(argv)
            # Write a file to simulate output_path being created
            for i, arg in enumerate(argv):
                if arg == "--output-last-message" and i + 1 < len(argv):
                    Path(argv[i + 1]).write_text('{"k": 1}', encoding="utf-8")
            return MagicMock(stdout="ignored")

        with (
            patch(
                "social_research_probe.technologies.llms.load_active_config",
                return_value=cfg,
            ),
            patch(
                "social_research_probe.technologies.llms.codex_cli.load_active_config",
                return_value=cfg,
            ),
            patch(
                "social_research_probe.utils.io.subprocess_runner.run",
                side_effect=fake_sp_run,
            ),
        ):
            out = CodexRunner().run("p", schema={"type": "object"})
        assert out == {"k": 1}
        assert "--output-schema" in captured_argv[0]

    def test_run_no_output_file_uses_stdout(self, monkeypatch):
        cfg = MagicMock()
        cfg.llm_settings.return_value = {"binary": "codex"}
        cfg.llm_timeout_seconds = 10

        def fake_sp_run(argv, **kw):
            return MagicMock(stdout='{"k": 2}')

        with (
            patch(
                "social_research_probe.technologies.llms.load_active_config",
                return_value=cfg,
            ),
            patch(
                "social_research_probe.technologies.llms.codex_cli.load_active_config",
                return_value=cfg,
            ),
            patch(
                "social_research_probe.utils.io.subprocess_runner.run",
                side_effect=fake_sp_run,
            ),
        ):
            out = CodexRunner().run("p")
        assert out == {"k": 2}


class TestCodexAgenticSearch:
    def test_failure(self, monkeypatch):
        cfg = MagicMock()
        cfg.llm_settings.return_value = {"binary": "codex"}

        def fake_sp_run(argv, **kw):
            raise OSError("boom")

        with (
            patch(
                "social_research_probe.technologies.llms.load_active_config",
                return_value=cfg,
            ),
            patch(
                "social_research_probe.utils.io.subprocess_runner.run",
                side_effect=fake_sp_run,
            ),
            pytest.raises(AdapterError),
        ):
            asyncio.run(CodexRunner().agentic_search("q"))

    def test_success(self, monkeypatch):
        cfg = MagicMock()
        cfg.llm_settings.return_value = {"binary": "codex"}

        def fake_sp_run(argv, **kw):
            for i, arg in enumerate(argv):
                if arg == "--output-last-message" and i + 1 < len(argv):
                    Path(argv[i + 1]).write_text(
                        json.dumps({"answer": "a", "citations": [{"url": "https://x"}]}),
                        encoding="utf-8",
                    )
            return MagicMock(stdout="ignored")

        with (
            patch(
                "social_research_probe.technologies.llms.load_active_config",
                return_value=cfg,
            ),
            patch(
                "social_research_probe.utils.io.subprocess_runner.run",
                side_effect=fake_sp_run,
            ),
        ):
            out = asyncio.run(CodexRunner().agentic_search("q"))
        assert out.answer == "a" and out.citations[0].url == "https://x"

    def test_success_no_file_uses_stdout(self, monkeypatch):
        cfg = MagicMock()
        cfg.llm_settings.return_value = {"binary": "codex"}

        def fake_sp_run(argv, **kw):
            return MagicMock(
                stdout=json.dumps({"answer": "z", "citations": []}),
            )

        with (
            patch(
                "social_research_probe.technologies.llms.load_active_config",
                return_value=cfg,
            ),
            patch(
                "social_research_probe.utils.io.subprocess_runner.run",
                side_effect=fake_sp_run,
            ),
        ):
            out = asyncio.run(CodexRunner().agentic_search("q"))
        assert out.answer == "z"

    def test_payload_not_dict(self, monkeypatch):
        cfg = MagicMock()
        cfg.llm_settings.return_value = {"binary": "codex"}

        def fake_sp_run(argv, **kw):
            return MagicMock(stdout=json.dumps([1, 2]))

        with (
            patch(
                "social_research_probe.technologies.llms.load_active_config",
                return_value=cfg,
            ),
            patch(
                "social_research_probe.utils.io.subprocess_runner.run",
                side_effect=fake_sp_run,
            ),
        ):
            out = asyncio.run(CodexRunner().agentic_search("q"))
        assert out.answer == ""
