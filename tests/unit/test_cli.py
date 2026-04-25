"""Tests for cli.py — the main argparse entry point.

Tests call main([...]) directly (in-process) with stubbed command modules
so no real file-system or API operations occur.
"""

from __future__ import annotations

import copy
import io
import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from social_research_probe.cli import _id_selector, main
from social_research_probe.commands import Command, ConfigSubcommand, ResearchCommand
from social_research_probe.technologies.report_render.html.raw_html.youtube import (
    serve_report_command,
)
from social_research_probe.utils.display.cli_output import _emit
from social_research_probe.cli.parsers import Arg
from social_research_probe.commands.install_skill import PackageManagerFlag

_VALID_PACKET = {
    "topic": "ai",
    "platform": "youtube",
    "purpose_set": ["latest-news"],
    "items_top_n": [],
    "source_validation_summary": {
        "validated": 0,
        "partially": 0,
        "unverified": 0,
        "low_trust": 0,
        "primary": 0,
        "secondary": 0,
        "commentary": 0,
        "notes": "",
    },
    "platform_engagement_summary": "0 items",
    "evidence_summary": "0 items",
    "stats_summary": {"models_run": [], "highlights": [], "low_confidence": False},
    "chart_captions": [],
    "warnings": [],
}


class TestEmitHelpers:
    def test_emit_json(self, capsys):
        _emit({"key": "val"}, "json")
        out = capsys.readouterr().out
        assert json.loads(out) == {"key": "val"}

    def test_emit_text_topics(self, capsys):
        _emit({"topics": ["a", "b"]}, "text")
        assert capsys.readouterr().out.strip() == "a\nb"

    def test_emit_text_no_topics(self, capsys):
        _emit({"topics": []}, "text")
        assert "(no topics)" in capsys.readouterr().out

    def test_emit_text_purposes(self, capsys):
        _emit({"purposes": {"p1": {"method": "m1"}}}, "text")
        assert "p1: m1" in capsys.readouterr().out

    def test_emit_text_no_purposes(self, capsys):
        _emit({"purposes": {}}, "text")
        assert "(no purposes)" in capsys.readouterr().out

    def test_emit_markdown(self, capsys):
        _emit("hello", "markdown")
        out = capsys.readouterr().out
        assert "```" in out and "hello" in out

    def test_emit_text_str(self, capsys):
        _emit("plain", "text")
        assert "plain" in capsys.readouterr().out

    def test_emit_text_fallback_json(self, capsys):
        _emit({"x": 1}, "text")
        assert json.loads(capsys.readouterr().out)


class TestIdSelector:
    def test_empty_string_returns_empty_list(self):
        assert _id_selector("") == []

    def test_all_returns_string_all(self):
        assert _id_selector("all") == "all"

    def test_comma_separated_ids(self):
        assert _id_selector("1,2,3") == [1, 2, 3]

    def test_invalid_id_raises_validation_error(self):
        from social_research_probe.errors import ValidationError

        with pytest.raises(ValidationError):
            _id_selector("abc")


class TestNoCommand:
    def test_no_command_returns_2(self):
        assert main([]) == 2

    def test_version_flag_exits_0(self, capsys):
        assert main([Arg.VERSION]) == 0
        out = capsys.readouterr().out
        assert "srp" in out
        assert "social_research_probe" in out


class TestShowTopics:
    def test_show_topics_text(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setattr(
            "social_research_probe.commands.topics.show_topics", lambda d: ["ai", "blockchain"]
        )
        assert main([Arg.DATA_DIR, str(tmp_path), Command.SHOW_TOPICS]) == 0
        assert "ai" in capsys.readouterr().out

    def test_show_topics_json(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setattr("social_research_probe.commands.topics.show_topics", lambda d: ["ai"])
        main([Arg.DATA_DIR, str(tmp_path), Command.SHOW_TOPICS, Arg.OUTPUT, "json"])
        out = json.loads(capsys.readouterr().out)
        assert out["topics"] == ["ai"]


class TestUpdateTopics:
    def test_add_topic(self, monkeypatch, tmp_path):
        calls = []
        monkeypatch.setattr(
            "social_research_probe.commands.topics.add_topics", lambda d, v, force: calls.append(v)
        )
        assert main([Arg.DATA_DIR, str(tmp_path), Command.UPDATE_TOPICS, Arg.ADD, '"ai"']) == 0
        assert len(calls) == 1

    def test_remove_topic(self, monkeypatch, tmp_path):
        calls = []
        monkeypatch.setattr(
            "social_research_probe.commands.topics.remove_topics", lambda d, v: calls.append(v)
        )
        assert main([Arg.DATA_DIR, str(tmp_path), Command.UPDATE_TOPICS, Arg.REMOVE, '"ai"']) == 0

    def test_rename_topic(self, monkeypatch, tmp_path):
        calls = []
        monkeypatch.setattr(
            "social_research_probe.commands.topics.rename_topic",
            lambda d, o, n: calls.append((o, n)),
        )
        assert (
            main([Arg.DATA_DIR, str(tmp_path), Command.UPDATE_TOPICS, Arg.RENAME, '"old"->"new"'])
            == 0
        )

    def test_rename_bad_format_raises(self, monkeypatch, tmp_path):
        result = main(
            [Arg.DATA_DIR, str(tmp_path), Command.UPDATE_TOPICS, Arg.RENAME, '"bad"-->"worse"']
        )
        assert result != 0


class TestShowPurposes:
    def test_show_purposes(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setattr(
            "social_research_probe.commands.purposes.show_purposes",
            lambda d: {"p1": {"method": "m1"}},
        )
        assert main([Arg.DATA_DIR, str(tmp_path), Command.SHOW_PURPOSES]) == 0
        assert "p1" in capsys.readouterr().out


class TestUpdatePurposes:
    def test_add_purpose(self, monkeypatch, tmp_path):
        calls = []
        monkeypatch.setattr(
            "social_research_probe.commands.purposes.add_purpose",
            lambda d, name, method, force: calls.append(name),
        )
        assert (
            main(
                [
                    Arg.DATA_DIR,
                    str(tmp_path),
                    Command.UPDATE_PURPOSES,
                    Arg.ADD,
                    '"name"="method desc"',
                ]
            )
            == 0
        )

    def test_add_purpose_bad_format_raises(self, monkeypatch, tmp_path):
        result = main([Arg.DATA_DIR, str(tmp_path), Command.UPDATE_PURPOSES, Arg.ADD, '"bad"'])
        assert result != 0

    def test_remove_purpose(self, monkeypatch, tmp_path):
        calls = []
        monkeypatch.setattr(
            "social_research_probe.commands.purposes.remove_purposes", lambda d, v: calls.append(v)
        )
        assert main([Arg.DATA_DIR, str(tmp_path), Command.UPDATE_PURPOSES, Arg.REMOVE, '"p1"']) == 0

    def test_rename_purpose(self, monkeypatch, tmp_path):
        calls = []
        monkeypatch.setattr(
            "social_research_probe.commands.purposes.rename_purpose",
            lambda d, o, n: calls.append((o, n)),
        )
        assert (
            main([Arg.DATA_DIR, str(tmp_path), Command.UPDATE_PURPOSES, Arg.RENAME, '"old"->"new"'])
            == 0
        )

    def test_rename_purpose_bad_format_raises(self, monkeypatch, tmp_path):
        result = main(
            [Arg.DATA_DIR, str(tmp_path), Command.UPDATE_PURPOSES, Arg.RENAME, '"bad"--"worse"']
        )
        assert result != 0


class TestSuggestTopics:
    def test_suggest_topics(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setattr(
            "social_research_probe.commands.suggestions.suggest_topics",
            lambda d, count: ["ai", "blockchain"],
        )
        monkeypatch.setattr(
            "social_research_probe.commands.suggestions.stage_suggestions",
            lambda d, topic_candidates, purpose_candidates: None,
        )
        assert main([Arg.DATA_DIR, str(tmp_path), ResearchCommand.SUGGEST_TOPICS]) == 0


class TestSuggestPurposes:
    def test_suggest_purposes(self, monkeypatch, tmp_path):
        monkeypatch.setattr(
            "social_research_probe.commands.suggestions.suggest_purposes",
            lambda d, count: [{"name": "p", "method": "m"}],
        )
        monkeypatch.setattr(
            "social_research_probe.commands.suggestions.stage_suggestions",
            lambda d, topic_candidates, purpose_candidates: None,
        )
        assert main([Arg.DATA_DIR, str(tmp_path), ResearchCommand.SUGGEST_PURPOSES]) == 0


class TestPending:
    def test_show_pending(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setattr(
            "social_research_probe.commands.suggestions.show_pending",
            lambda d: {"topic_candidates": [], "purpose_candidates": []},
        )
        assert main([Arg.DATA_DIR, str(tmp_path), Command.SHOW_PENDING]) == 0

    def test_apply_pending(self, monkeypatch, tmp_path):
        calls = []
        monkeypatch.setattr(
            "social_research_probe.commands.suggestions.apply_pending",
            lambda d, topic_ids, purpose_ids: calls.append(1),
        )
        assert main([Arg.DATA_DIR, str(tmp_path), Command.APPLY_PENDING, Arg.TOPICS, "all"]) == 0

    def test_discard_pending(self, monkeypatch, tmp_path):
        calls = []
        monkeypatch.setattr(
            "social_research_probe.commands.suggestions.discard_pending",
            lambda d, topic_ids, purpose_ids: calls.append(1),
        )
        assert main([Arg.DATA_DIR, str(tmp_path), Command.DISCARD_PENDING, Arg.TOPICS, "1,2"]) == 0


class TestStageSuggestions:
    def test_stage_from_stdin(self, monkeypatch, tmp_path):
        payload = json.dumps({"topic_candidates": ["x"], "purpose_candidates": []})
        monkeypatch.setattr("sys.stdin", io.StringIO(payload))
        monkeypatch.setattr(
            "social_research_probe.commands.suggestions.stage_suggestions",
            lambda d, topic_candidates, purpose_candidates: None,
        )
        assert main([Arg.DATA_DIR, str(tmp_path), Command.STAGE_SUGGESTIONS, Arg.FROM_STDIN]) == 0

    def test_stage_without_from_stdin_raises(self, monkeypatch, tmp_path):
        result = main([Arg.DATA_DIR, str(tmp_path), Command.STAGE_SUGGESTIONS])
        assert result != 0

    def test_stage_invalid_json_raises(self, monkeypatch, tmp_path):
        monkeypatch.setattr("sys.stdin", io.StringIO("not json"))
        result = main([Arg.DATA_DIR, str(tmp_path), Command.STAGE_SUGGESTIONS, Arg.FROM_STDIN])
        assert result != 0


class TestResearchCommand:
    def test_research(self, monkeypatch, tmp_path, capsys):
        calls = []
        monkeypatch.setattr(
            "social_research_probe.pipeline.run_pipeline",
            AsyncMock(
                side_effect=lambda cmd, d, adapter_config=None: (
                    calls.append(adapter_config) or copy.deepcopy(_VALID_PACKET)
                )
            ),
        )
        monkeypatch.setattr("social_research_probe.cli._attach_synthesis", lambda pkt: None)
        assert (
            main(
                [
                    Arg.DATA_DIR,
                    str(tmp_path),
                    "research",
                    "youtube",
                    "AI",
                    "latest-news",
                ]
            )
            == 0
        )
        assert calls == [{"include_shorts": True, "fetch_transcripts": True}]
        out = capsys.readouterr().out.strip()
        assert out.endswith(".html") or out.endswith(".md")


class TestServeReportCommand:
    def test_serve_report_dispatch(self, monkeypatch, tmp_path):
        report = tmp_path / "report.html"
        report.write_text("<html></html>", encoding="utf-8")
        calls = []

        monkeypatch.setattr(
            "social_research_probe.commands.serve_report.run",
            lambda report_path, host, port, voicebox_base: (
                calls.append((report_path, host, port, voicebox_base)) or 0
            ),
        )

        result = main(
            [
                Arg.DATA_DIR,
                str(tmp_path),
                "serve-report",
                Arg.REPORT,
                str(report),
                Arg.HOST,
                "127.0.0.1",
                Arg.PORT,
                "9001",
                Arg.VOICEBOX_BASE,
                "http://127.0.0.1:17493",
            ]
        )

        assert result == 0
        assert calls == [(str(report), "127.0.0.1", 9001, "http://127.0.0.1:17493")]


class TestInstallSkillTargetValidation:
    def test_install_skill_target_outside_home_raises(self, monkeypatch, tmp_path):
        """install-skill rejects --target paths outside ~/.claude/."""
        monkeypatch.setattr("pathlib.Path.home", classmethod(lambda cls: tmp_path))
        result = main(["install-skill", Arg.TARGET, "/tmp/dangerous"])
        assert result != 0


class TestSetup:
    def test_setup_runs_config_copy_and_both_prompts(self, monkeypatch, tmp_path):
        """`srp setup` invokes the config copy + runner + secrets prompts and exits 0."""
        calls: list[str] = []
        monkeypatch.setattr(
            "social_research_probe.commands.setup._copy_config_example",
            lambda d: calls.append("config"),
        )
        monkeypatch.setattr(
            "social_research_probe.commands.setup._prompt_for_runner",
            lambda d: calls.append("runner"),
        )
        monkeypatch.setattr(
            "social_research_probe.commands.setup._prompt_for_secrets",
            lambda d: calls.append("secrets"),
        )
        result = main([Arg.DATA_DIR, str(tmp_path), "setup"])
        assert result == 0
        assert calls == ["secrets", "config", "runner"]


class TestInstallSkill:
    def test_install_skill(self, monkeypatch, tmp_path):
        monkeypatch.setattr("pathlib.Path.home", classmethod(lambda cls: tmp_path))
        target = tmp_path / ".claude" / "skill_out"
        monkeypatch.setattr(
            "shutil.copytree", lambda s, d: target.mkdir(parents=True, exist_ok=True)
        )
        monkeypatch.setattr("shutil.which", lambda x: None)
        monkeypatch.setattr("shutil.rmtree", lambda d: None)
        monkeypatch.setattr(
            "social_research_probe.commands.install_skill._prompt_for_secrets", lambda d: None
        )
        monkeypatch.setattr(
            "social_research_probe.commands.install_skill._copy_config_example", lambda d: None
        )
        monkeypatch.setattr(
            "social_research_probe.commands.install_skill._prompt_for_runner", lambda d: None
        )
        result = main(["install-skill", Arg.TARGET, str(target)])
        assert result == 0


class TestConfig:
    def test_config_show(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setattr(
            "social_research_probe.commands.config.show_config", lambda d: "config output"
        )
        assert main([Arg.DATA_DIR, str(tmp_path), Command.CONFIG, ConfigSubcommand.SHOW]) == 0
        assert "config output" in capsys.readouterr().out

    def test_config_path(self, monkeypatch, tmp_path, capsys):
        assert main([Arg.DATA_DIR, str(tmp_path), Command.CONFIG, ConfigSubcommand.PATH]) == 0
        out = capsys.readouterr().out
        assert "config" in out

    def test_config_set(self, monkeypatch, tmp_path):
        calls = []
        monkeypatch.setattr(
            "social_research_probe.commands.config.write_config_value",
            lambda d, k, v: calls.append((k, v)),
        )
        assert (
            main(
                [Arg.DATA_DIR, str(tmp_path), Command.CONFIG, ConfigSubcommand.SET, "key", "value"]
            )
            == 0
        )

    def test_config_set_secret_from_stdin(self, monkeypatch, tmp_path):
        monkeypatch.setattr("sys.stdin", io.StringIO("my-secret"))
        calls = []
        monkeypatch.setattr(
            "social_research_probe.commands.config.write_secret", lambda d, n, v: calls.append(v)
        )
        assert (
            main(
                [
                    Arg.DATA_DIR,
                    str(tmp_path),
                    Command.CONFIG,
                    ConfigSubcommand.SET_SECRET,
                    "my_key",
                    Arg.FROM_STDIN,
                ]
            )
            == 0
        )

    def test_config_set_secret_empty_raises(self, monkeypatch, tmp_path):
        monkeypatch.setattr("sys.stdin", io.StringIO(""))
        result = main(
            [Arg.DATA_DIR, str(tmp_path), "config", "set-secret", "my_key", Arg.FROM_STDIN]
        )
        assert result != 0

    def test_config_set_secret_via_getpass(self, monkeypatch, tmp_path):
        """The else branch (no --from-stdin) reads the secret via getpass."""
        import sys
        import types

        calls = []
        monkeypatch.setattr(
            "social_research_probe.commands.config.write_secret",
            lambda d, n, v: calls.append(v),
        )
        fake_getpass_mod = types.ModuleType("getpass")
        fake_getpass_mod.getpass = lambda prompt="": "secret-from-tty"
        monkeypatch.setitem(sys.modules, "getpass", fake_getpass_mod)

        result = main(
            [Arg.DATA_DIR, str(tmp_path), Command.CONFIG, ConfigSubcommand.SET_SECRET, "my_key"]
        )
        assert result == 0
        assert calls == ["secret-from-tty"]

    def test_config_unset_secret(self, monkeypatch, tmp_path):
        calls = []
        monkeypatch.setattr(
            "social_research_probe.commands.config.unset_secret", lambda d, n: calls.append(n)
        )
        assert (
            main(
                [
                    Arg.DATA_DIR,
                    str(tmp_path),
                    Command.CONFIG,
                    ConfigSubcommand.UNSET_SECRET,
                    "my_key",
                ]
            )
            == 0
        )

    def test_config_check_secrets(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setattr(
            "social_research_probe.commands.config.check_secrets",
            lambda d, needed_for, platform, corroboration: {"missing": []},
        )
        assert (
            main(
                [
                    Arg.DATA_DIR,
                    str(tmp_path),
                    Command.CONFIG,
                    ConfigSubcommand.CHECK_SECRETS,
                    Arg.OUTPUT,
                    "json",
                ]
            )
            == 0
        )

    def test_config_unknown_subcommand_returns_2(self, monkeypatch, tmp_path):
        # config with no subcommand → returns 2
        result = main([Arg.DATA_DIR, str(tmp_path), Command.CONFIG])
        assert result == 2


class TestCorroborateClaims:
    def test_corroborate_claims(self, monkeypatch, tmp_path, capsys):
        claims_file = tmp_path / "claims.json"
        claims_file.write_text(
            json.dumps({"claims": [{"text": "AI is growing.", "source_text": "..."}]})
        )
        monkeypatch.setattr(
            "social_research_probe.commands.corroborate_claims.corroborate_claim",
            AsyncMock(return_value={"claim_text": "AI is growing.", "results": []}),
        )
        assert (
            main([Arg.DATA_DIR, str(tmp_path), "corroborate-claims", Arg.INPUT, str(claims_file)])
            == 0
        )


class TestRender:
    def test_render(self, monkeypatch, tmp_path, capsys):
        from social_research_probe.stats.base import StatResult
        from social_research_probe.viz.base import ChartResult

        packet_file = tmp_path / "packet.json"
        packet_file.write_text(json.dumps({"items_top_n": [{"scores": {"overall": 0.75}}]}))
        monkeypatch.setattr(
            "social_research_probe.commands.render.select_and_run",
            lambda d, label: [StatResult("x", 1.0, "caption")],
        )
        monkeypatch.setattr(
            "social_research_probe.commands.render.select_and_render",
            lambda d, label, output_dir: ChartResult("/tmp/x.png", "cap"),
        )
        assert main([Arg.DATA_DIR, str(tmp_path), "render", Arg.PACKET, str(packet_file)]) == 0


class TestSrpErrorHandling:
    def test_srp_error_returns_exit_code(self, monkeypatch, tmp_path):
        from social_research_probe.errors import ValidationError

        monkeypatch.setattr(
            "social_research_probe.commands.topics.show_topics",
            lambda d: (_ for _ in ()).throw(ValidationError("bad")),
        )
        result = main([Arg.DATA_DIR, str(tmp_path), Command.SHOW_TOPICS])
        assert result == 2


class TestInstallSkillWithUvOrPipx:
    def test_install_skill_with_uv(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setattr("pathlib.Path.home", classmethod(lambda cls: tmp_path))
        target = tmp_path / ".claude" / "skill_out"
        monkeypatch.setattr(
            "shutil.copytree", lambda s, d: target.mkdir(parents=True, exist_ok=True)
        )
        monkeypatch.setattr("shutil.rmtree", lambda d: None)
        calls = []
        monkeypatch.setattr(
            "shutil.which",
            lambda x: "/usr/local/bin/uv" if x == "uv" else None,
        )
        monkeypatch.setattr(
            "subprocess.run",
            lambda cmd, check: calls.append(cmd),
        )
        monkeypatch.setattr(
            "social_research_probe.commands.install_skill._prompt_for_secrets", lambda d: None
        )
        monkeypatch.setattr(
            "social_research_probe.commands.install_skill._copy_config_example", lambda d: None
        )
        monkeypatch.setattr(
            "social_research_probe.commands.install_skill._prompt_for_runner", lambda d: None
        )
        result = main(["install-skill", Arg.TARGET, str(target)])
        assert result == 0
        assert calls == [
            [
                "uv",
                "tool",
                "install",
                Arg.FORCE,
                PackageManagerFlag.REINSTALL,
                "git+https://github.com/reshinto/social-research-probe",
            ]
        ]
        out = capsys.readouterr().out
        assert "uv" in out

    def test_install_skill_with_pipx(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setattr("pathlib.Path.home", classmethod(lambda cls: tmp_path))
        target = tmp_path / ".claude" / "skill_out"
        monkeypatch.setattr(
            "shutil.copytree", lambda s, d: target.mkdir(parents=True, exist_ok=True)
        )
        monkeypatch.setattr("shutil.rmtree", lambda d: None)
        calls = []
        monkeypatch.setattr(
            "shutil.which",
            lambda x: "/usr/local/bin/pipx" if x == "pipx" else None,
        )
        monkeypatch.setattr(
            "subprocess.run",
            lambda cmd, check: calls.append(cmd),
        )
        monkeypatch.setattr(
            "social_research_probe.commands.install_skill._prompt_for_secrets", lambda d: None
        )
        monkeypatch.setattr(
            "social_research_probe.commands.install_skill._copy_config_example", lambda d: None
        )
        monkeypatch.setattr(
            "social_research_probe.commands.install_skill._prompt_for_runner", lambda d: None
        )
        result = main(["install-skill", Arg.TARGET, str(target)])
        assert result == 0
        assert any("pipx" in str(c) for c in calls)
        out = capsys.readouterr().out
        assert "pipx" in out


class TestInstallSkillDestExists:
    def test_install_skill_dest_exists_calls_rmtree(self, monkeypatch, tmp_path, capsys):
        """Line 257: shutil.rmtree called when dest already exists."""
        monkeypatch.setattr("pathlib.Path.home", classmethod(lambda cls: tmp_path))
        target = tmp_path / ".claude" / "skill_out"
        target.mkdir(parents=True)  # make it exist so dest.exists() is True
        rmtree_calls = []
        monkeypatch.setattr("shutil.rmtree", lambda d: rmtree_calls.append(d))
        monkeypatch.setattr("shutil.copytree", lambda s, d: None)
        monkeypatch.setattr("shutil.which", lambda x: None)
        monkeypatch.setattr(
            "social_research_probe.commands.install_skill._prompt_for_secrets", lambda d: None
        )
        monkeypatch.setattr(
            "social_research_probe.commands.install_skill._copy_config_example", lambda d: None
        )
        monkeypatch.setattr(
            "social_research_probe.commands.install_skill._prompt_for_runner", lambda d: None
        )
        result = main(["install-skill", Arg.TARGET, str(target)])
        assert result == 0
        assert len(rmtree_calls) == 1


class TestDispatchFallthrough:
    def test_dispatch_returns_2_for_unknown_command(self, monkeypatch, tmp_path):
        """Line 275: _dispatch returns 2 when command not matched."""
        import argparse

        from social_research_probe.cli import _dispatch

        args = argparse.Namespace(command="nonexistent-command", data_dir=str(tmp_path))
        result = _dispatch(args)
        assert result == 2


class TestSimpleResearch:
    def _patch_pipeline(self, monkeypatch, captured):
        async def fake(cmd, d, adapter_config=None):
            captured.append((cmd, adapter_config))
            return copy.deepcopy(_VALID_PACKET)

        monkeypatch.setattr("social_research_probe.pipeline.run_pipeline", fake)
        monkeypatch.setattr("social_research_probe.cli._attach_synthesis", lambda pkt: None)

    def test_default_platform_is_youtube(self, monkeypatch, tmp_path):
        captured = []
        self._patch_pipeline(monkeypatch, captured)
        assert main([Arg.DATA_DIR, str(tmp_path), "research", "ai", "latest-news"]) == 0
        cmd, cfg = captured[0]
        assert cmd.platform == "youtube"
        assert cmd.topics == [("ai", ["latest-news"])]
        assert cfg == {"include_shorts": True, "fetch_transcripts": True}

    def test_explicit_platform_positional(self, monkeypatch, tmp_path):
        captured = []
        self._patch_pipeline(monkeypatch, captured)
        main([Arg.DATA_DIR, str(tmp_path), "research", "youtube", "ai", "latest-news"])
        cmd, _cfg = captured[0]
        assert cmd.platform == "youtube"

    def test_multiple_purposes_comma_separated(self, monkeypatch, tmp_path):
        captured = []
        self._patch_pipeline(monkeypatch, captured)
        main([Arg.DATA_DIR, str(tmp_path), "research", "ai", "latest-news,trends"])
        cmd, _cfg = captured[0]
        assert cmd.topics == [("ai", ["latest-news", "trends"])]

    def test_no_shorts_flag_disables_shorts(self, monkeypatch, tmp_path):
        captured = []
        self._patch_pipeline(monkeypatch, captured)
        main([Arg.DATA_DIR, str(tmp_path), "research", "ai", "latest-news", Arg.NO_SHORTS])
        _cmd, cfg = captured[0]
        assert cfg == {"include_shorts": False, "fetch_transcripts": True}

    def test_too_few_args_returns_validation_exit_code(self, monkeypatch, tmp_path):
        # "srp research ai" triggers NL query mode. With runner="none" (the default
        # in test configs), classify_query raises ValidationError, so the exit code
        # is still ValidationError.exit_code — the same value as before this change.
        from social_research_probe.errors import ValidationError

        captured = []
        self._patch_pipeline(monkeypatch, captured)
        assert main([Arg.DATA_DIR, str(tmp_path), "research", "ai"]) == ValidationError.exit_code

    def test_empty_purpose_arg_returns_validation_exit_code(self, monkeypatch, tmp_path):
        from social_research_probe.errors import ValidationError

        captured = []
        self._patch_pipeline(monkeypatch, captured)
        assert (
            main([Arg.DATA_DIR, str(tmp_path), "research", "ai", ","]) == ValidationError.exit_code
        )

    def test_nl_query_dispatches_classify_then_run_research(self, monkeypatch, tmp_path):
        # NL query mode: single non-platform positional → classify_query is called,
        # and topic/purposes are taken from the ClassifiedQuery result.
        from social_research_probe.services.llm.classify_query import ClassifiedQuery

        def fake_classify_query(query, *, data_dir, cfg):
            return ClassifiedQuery(
                topic="quant-finance",
                purpose_name="job-opportunities",
                purpose_method="career paths in quant funds",
                topic_created=True,
                purpose_created=True,
            )

        monkeypatch.setattr(
            "social_research_probe.commands.nl_query.classify_query", fake_classify_query
        )
        captured = []
        self._patch_pipeline(monkeypatch, captured)
        rc = main(
            [Arg.DATA_DIR, str(tmp_path), "research", "youtube", "i want to know about quant jobs"]
        )
        assert rc == 0
        cmd, _cfg = captured[0]
        assert cmd.topics == [("quant-finance", ["job-opportunities"])]
        assert cmd.platform == "youtube"

    def test_nl_query_default_platform_is_youtube(self, monkeypatch, tmp_path):
        # When no platform is specified, NL query mode defaults to youtube.
        from social_research_probe.services.llm.classify_query import ClassifiedQuery

        def fake_classify_query(query, *, data_dir, cfg):
            return ClassifiedQuery(
                topic="ai",
                purpose_name="trends",
                purpose_method="current trends",
                topic_created=False,
                purpose_created=False,
            )

        monkeypatch.setattr(
            "social_research_probe.commands.nl_query.classify_query", fake_classify_query
        )
        captured = []
        self._patch_pipeline(monkeypatch, captured)
        rc = main([Arg.DATA_DIR, str(tmp_path), "research", "i want to know about ai trends"])
        assert rc == 0
        cmd, _cfg = captured[0]
        assert cmd.platform == "youtube"
        assert cmd.topics == [("ai", ["trends"])]

    def test_platform_only_arg_returns_validation_exit_code(self, monkeypatch, tmp_path):
        # "srp research youtube" — platform given but no topic/purpose follows.
        # _parse_simple_research_args raises ValidationError for this case.
        from social_research_probe.errors import ValidationError

        captured = []
        self._patch_pipeline(monkeypatch, captured)
        assert (
            main([Arg.DATA_DIR, str(tmp_path), "research", "youtube"]) == ValidationError.exit_code
        )


class TestSimpleResearchTranscripts:
    def _patch_pipeline(self, monkeypatch, captured):
        async def fake(cmd, d, adapter_config=None):
            captured.append((cmd, adapter_config))
            return copy.deepcopy(_VALID_PACKET)

        monkeypatch.setattr("social_research_probe.pipeline.run_pipeline", fake)
        monkeypatch.setattr("social_research_probe.cli._attach_synthesis", lambda pkt: None)

    def test_no_transcripts_flag_disables_transcripts(self, monkeypatch, tmp_path):
        captured = []
        self._patch_pipeline(monkeypatch, captured)
        main([Arg.DATA_DIR, str(tmp_path), "research", "ai", "latest-news", Arg.NO_TRANSCRIPTS])
        _cmd, cfg = captured[0]
        assert cfg["fetch_transcripts"] is False


class TestPromptForSecrets:
    """Unit tests for install_skill._prompt_for_secrets."""

    def _run(self, tmp_path, inputs, monkeypatch):
        """Helper: run _prompt_for_secrets with a canned sequence of inputs."""
        from social_research_probe.commands.install_skill import _prompt_for_secrets

        seq = iter(inputs)
        _prompt_for_secrets(tmp_path, _input=lambda prompt="": next(seq))

    def test_blank_inputs_skip_all_keys(self, tmp_path, monkeypatch):
        """Every blank response must not write any secret."""
        write_calls = []
        monkeypatch.setattr(
            "social_research_probe.commands.config.write_secret",
            lambda d, n, v: write_calls.append(n),
        )
        monkeypatch.setattr("social_research_probe.commands.config.read_secret", lambda d, n: None)
        self._run(tmp_path, ["", "  ", "", ""], monkeypatch)
        assert write_calls == []

    def test_key_without_url_skips_register_line(self, tmp_path, monkeypatch):
        import social_research_probe.commands.install_skill as mod

        monkeypatch.setattr(mod, "_KEY_PROMPTS", [("test_key", "Test key", "")])
        monkeypatch.setattr("social_research_probe.commands.config.read_secret", lambda d, n: None)
        monkeypatch.setattr(
            "social_research_probe.commands.config.write_secret", lambda d, n, v: None
        )
        from social_research_probe.commands.install_skill import _prompt_for_secrets

        _prompt_for_secrets(tmp_path, _input=lambda p="": "")

    def test_provided_values_are_written(self, tmp_path, monkeypatch):
        """Non-blank answers must be persisted via write_secret."""
        written = {}
        monkeypatch.setattr(
            "social_research_probe.commands.config.write_secret",
            lambda d, n, v: written.update({n: v}),
        )
        monkeypatch.setattr("social_research_probe.commands.config.read_secret", lambda d, n: None)
        self._run(tmp_path, ["yt-key", "", "exa-key", ""], monkeypatch)
        assert written == {"youtube_api_key": "yt-key", "exa_api_key": "exa-key"}

    def test_existing_secret_shown_masked_in_prompt(self, tmp_path, monkeypatch):
        """When a secret already exists, its masked value appears in the prompt text."""
        from social_research_probe.commands.install_skill import _prompt_for_secrets

        monkeypatch.setattr(
            "social_research_probe.commands.config.read_secret",
            lambda d, n: "abcd1234efgh5678" if n == "youtube_api_key" else None,
        )
        monkeypatch.setattr(
            "social_research_probe.commands.config.write_secret", lambda d, n, v: None
        )
        prompts: list[str] = []
        _prompt_for_secrets(tmp_path, _input=lambda p="": prompts.append(p) or "")
        assert any("abcd...5678" in p for p in prompts)

    def test_eoferror_breaks_loop_gracefully(self, tmp_path, monkeypatch):
        """EOFError on first prompt must not raise and must not write anything."""
        write_calls = []
        monkeypatch.setattr(
            "social_research_probe.commands.config.write_secret",
            lambda d, n, v: write_calls.append(n),
        )
        monkeypatch.setattr("social_research_probe.commands.config.read_secret", lambda d, n: None)
        from social_research_probe.commands.install_skill import _prompt_for_secrets

        _prompt_for_secrets(tmp_path, _input=lambda prompt="": (_ for _ in ()).throw(EOFError()))
        assert write_calls == []

    def test_keyboardinterrupt_breaks_loop_gracefully(self, tmp_path, monkeypatch):
        """KeyboardInterrupt must be caught and must not write anything."""
        write_calls = []
        monkeypatch.setattr(
            "social_research_probe.commands.config.write_secret",
            lambda d, n, v: write_calls.append(n),
        )
        monkeypatch.setattr("social_research_probe.commands.config.read_secret", lambda d, n: None)
        from social_research_probe.commands.install_skill import _prompt_for_secrets

        _prompt_for_secrets(
            tmp_path, _input=lambda prompt="": (_ for _ in ()).throw(KeyboardInterrupt())
        )
        assert write_calls == []


class TestCopyConfigExample:
    """Unit tests for install_skill._copy_config_example."""

    def test_bundled_config_uses_repo_root_template(self):
        from social_research_probe.commands.install_skill import _BUNDLED_CONFIG

        assert Path("config.toml.example").resolve() == _BUNDLED_CONFIG
        assert _BUNDLED_CONFIG.exists()

    def test_copies_example_when_config_absent(self, tmp_path):
        from social_research_probe.commands.install_skill import _copy_config_example

        _copy_config_example(tmp_path)
        assert (tmp_path / "config.toml").exists()

    def test_preserves_user_values_when_config_exists(self, tmp_path):
        from social_research_probe.commands.install_skill import _copy_config_example

        existing = tmp_path / "config.toml"
        existing.write_text('[llm]\nrunner = "claude"\ntimeout_seconds = 42\n', encoding="utf-8")
        _copy_config_example(tmp_path)
        content = existing.read_text(encoding="utf-8")
        assert 'runner = "claude"' in content
        assert "timeout_seconds = 42" in content

    def test_merges_missing_keys_when_config_exists(self, tmp_path):
        import tomllib

        from social_research_probe.commands.install_skill import _copy_config_example

        existing = tmp_path / "config.toml"
        existing.write_text('[llm]\nrunner = "claude"\n', encoding="utf-8")
        _copy_config_example(tmp_path)
        merged = tomllib.loads(existing.read_text(encoding="utf-8"))
        assert merged["llm"]["runner"] == "claude"
        assert "stages" in merged
        assert "services" in merged
        assert "technologies" in merged
        assert "platforms" in merged

    def test_merge_is_idempotent(self, tmp_path):
        from social_research_probe.commands.install_skill import _copy_config_example

        _copy_config_example(tmp_path)
        first = (tmp_path / "config.toml").read_text(encoding="utf-8")
        _copy_config_example(tmp_path)
        second = (tmp_path / "config.toml").read_text(encoding="utf-8")
        assert first == second

    def test_creates_data_dir_when_absent(self, tmp_path):
        from social_research_probe.commands.install_skill import _copy_config_example

        target = tmp_path / "nested" / "data"
        _copy_config_example(target)
        assert (target / "config.toml").exists()


class TestPromptForRunner:
    """Unit tests for install_skill._prompt_for_runner."""

    def test_valid_choice_writes_runner(self, tmp_path, monkeypatch):
        from social_research_probe.commands.install_skill import _prompt_for_runner

        written = {}
        monkeypatch.setattr(
            "social_research_probe.commands.config.write_config_value",
            lambda d, k, v: written.update({k: v}),
        )
        _prompt_for_runner(tmp_path, _input=lambda p="": "1")  # 1 = claude
        assert written == {
            "llm.runner": "claude",
            "technologies.claude": "true",
        }

    def test_none_choice_writes_none(self, tmp_path, monkeypatch):
        from social_research_probe.commands.install_skill import _prompt_for_runner

        written = {}
        monkeypatch.setattr(
            "social_research_probe.commands.config.write_config_value",
            lambda d, k, v: written.update({k: v}),
        )
        _prompt_for_runner(tmp_path, _input=lambda p="": "5")  # 5 = none
        assert written == {"llm.runner": "none"}

    def test_blank_input_skips(self, tmp_path, monkeypatch):
        from social_research_probe.commands.install_skill import _prompt_for_runner

        calls = []
        monkeypatch.setattr(
            "social_research_probe.commands.config.write_config_value",
            lambda d, k, v: calls.append(v),
        )
        _prompt_for_runner(tmp_path, _input=lambda p="": "")
        assert calls == []

    def test_invalid_choice_skips(self, tmp_path, monkeypatch):
        from social_research_probe.commands.install_skill import _prompt_for_runner

        calls = []
        monkeypatch.setattr(
            "social_research_probe.commands.config.write_config_value",
            lambda d, k, v: calls.append(v),
        )
        _prompt_for_runner(tmp_path, _input=lambda p="": "99")
        assert calls == []

    def test_eoferror_skips(self, tmp_path, monkeypatch):
        from social_research_probe.commands.install_skill import _prompt_for_runner

        calls = []
        monkeypatch.setattr(
            "social_research_probe.commands.config.write_config_value",
            lambda d, k, v: calls.append(v),
        )
        _prompt_for_runner(tmp_path, _input=lambda p="": (_ for _ in ()).throw(EOFError()))
        assert calls == []

    def test_keyboardinterrupt_skips(self, tmp_path, monkeypatch):
        from social_research_probe.commands.install_skill import _prompt_for_runner

        calls = []
        monkeypatch.setattr(
            "social_research_probe.commands.config.write_config_value",
            lambda d, k, v: calls.append(v),
        )
        _prompt_for_runner(tmp_path, _input=lambda p="": (_ for _ in ()).throw(KeyboardInterrupt()))
        assert calls == []


class TestRequiredSynthesis:
    """Unit tests for cli._run_required_synthesis and envelope output."""

    def test_returns_none_when_synthesis_stage_disabled(self, monkeypatch):
        from social_research_probe.commands.research import _run_required_synthesis

        class _Cfg:
            default_structured_runner = "claude"

            def stage_enabled(self, name: str) -> bool:
                return name != "synthesis"

        monkeypatch.setattr("social_research_probe.cli.load_active_config", lambda: _Cfg())
        assert _run_required_synthesis({}) is None

    def test_returns_none_when_runner_is_none(self, monkeypatch):
        from social_research_probe.commands.research import _run_required_synthesis

        class _Cfg:
            default_structured_runner = "none"

        monkeypatch.setattr("social_research_probe.cli.load_active_config", lambda: _Cfg())
        assert _run_required_synthesis({}) is None

    def test_returns_none_when_llm_service_disabled(self, monkeypatch):
        from social_research_probe.commands.research import _run_required_synthesis

        class _Cfg:
            default_structured_runner = "claude"

            def service_enabled(self, name: str) -> bool:
                return name != "llm"

        monkeypatch.setattr("social_research_probe.cli.load_active_config", lambda: _Cfg())
        assert _run_required_synthesis({}) is None

    def test_returns_synthesis_on_success(self, monkeypatch):
        from social_research_probe.commands.research import _run_required_synthesis

        class _Cfg:
            default_structured_runner = "claude"

        captured = {}

        class _Runner:
            def health_check(self) -> bool:
                return True

            def run(self, prompt, *, schema=None):
                captured["schema"] = schema
                return {
                    "compiled_synthesis": "compiled synthesis text",
                    "opportunity_analysis": "opportunity analysis text",
                    "report_summary": "final summary text",
                }

        monkeypatch.setattr("social_research_probe.cli.load_active_config", lambda: _Cfg())
        monkeypatch.setattr("social_research_probe.cli.get_runner", lambda name: _Runner())
        result = _run_required_synthesis(_VALID_PACKET)
        assert result == {
            "compiled_synthesis": "compiled synthesis text",
            "opportunity_analysis": "opportunity analysis text",
            "report_summary": "final summary text",
        }
        assert captured["schema"]["type"] == "object"
        assert set(captured["schema"]["required"]) == {
            "compiled_synthesis",
            "opportunity_analysis",
            "report_summary",
        }

    def test_returns_none_when_all_runners_fail(self, monkeypatch):
        from social_research_probe.commands.research import _run_required_synthesis

        class _Cfg:
            default_structured_runner = "claude"

        monkeypatch.setattr("social_research_probe.cli.load_active_config", lambda: _Cfg())
        monkeypatch.setattr(
            "social_research_probe.cli.get_runner",
            lambda name: (_ for _ in ()).throw(RuntimeError("no cli")),
        )
        assert _run_required_synthesis(_VALID_PACKET) is None

    def test_returns_none_when_all_runners_unavailable(self, monkeypatch):
        from social_research_probe.commands.research import _run_required_synthesis

        class _Cfg:
            default_structured_runner = "gemini"

        class _Runner:
            def health_check(self) -> bool:
                return False

        monkeypatch.setattr("social_research_probe.cli.load_active_config", lambda: _Cfg())
        monkeypatch.setattr("social_research_probe.cli.get_runner", lambda name: _Runner())
        assert _run_required_synthesis(_VALID_PACKET) is None

    def test_skips_runners_disabled_by_technology_config(self, monkeypatch):
        from social_research_probe.commands.research import _run_required_synthesis

        class _Cfg:
            default_structured_runner = "gemini"

            def technology_enabled(self, name: str) -> bool:
                return False

        monkeypatch.setattr("social_research_probe.cli.load_active_config", lambda: _Cfg())
        monkeypatch.setattr(
            "social_research_probe.cli.get_runner",
            lambda name: (_ for _ in ()).throw(AssertionError("runner lookup should be skipped")),
        )
        assert _run_required_synthesis(_VALID_PACKET) is None

    def test_falls_back_when_preferred_structured_runner_fails(self, monkeypatch):
        from social_research_probe.commands.research import _run_required_synthesis

        class _Cfg:
            default_structured_runner = "gemini"

        calls = []

        class _GeminiRunner:
            def health_check(self) -> bool:
                calls.append("gemini.health")
                return True

            def run(self, prompt, *, schema=None):
                calls.append("gemini.run")
                raise RuntimeError("gemini unavailable")

        class _CodexRunner:
            def health_check(self) -> bool:
                calls.append("codex.health")
                return True

            def run(self, prompt, *, schema=None):
                calls.append("codex.run")
                return {
                    "compiled_synthesis": "compiled synthesis text",
                    "opportunity_analysis": "opportunity analysis text",
                    "report_summary": "final summary text",
                }

        def fake_get_runner(name: str):
            if name == "gemini":
                return _GeminiRunner()
            if name == "codex":
                return _CodexRunner()

            class _MissingRunner:
                def health_check(self) -> bool:
                    calls.append(f"{name}.health")
                    return False

            return _MissingRunner()

        monkeypatch.setattr("social_research_probe.cli.load_active_config", lambda: _Cfg())
        monkeypatch.setattr("social_research_probe.cli.get_runner", fake_get_runner)
        assert _run_required_synthesis(_VALID_PACKET) == {
            "compiled_synthesis": "compiled synthesis text",
            "opportunity_analysis": "opportunity analysis text",
            "report_summary": "final summary text",
        }
        assert calls == [
            "gemini.health",
            "gemini.run",
            "claude.health",
            "codex.health",
            "codex.run",
        ]

    def test_research_emits_envelope_with_html_path(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setattr(
            "social_research_probe.pipeline.run_pipeline",
            AsyncMock(return_value=copy.deepcopy(_VALID_PACKET)),
        )
        monkeypatch.setattr(
            "social_research_probe.cli._attach_synthesis",
            lambda pkt: pkt.update(
                {
                    "compiled_synthesis": "synth10",
                    "opportunity_analysis": "synth11",
                    "report_summary": "synth12",
                }
            ),
        )
        main([Arg.DATA_DIR, str(tmp_path), "research", "youtube", "AI", "latest-news"])
        out = capsys.readouterr().out.strip()
        reports = list((tmp_path / "reports").glob("*.html"))
        assert len(reports) == 1
        assert out == serve_report_command(reports[0])

    def test_no_html_still_emits_synthesized_packet(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setattr(
            "social_research_probe.pipeline.run_pipeline",
            AsyncMock(return_value=copy.deepcopy(_VALID_PACKET)),
        )
        monkeypatch.setattr(
            "social_research_probe.cli._attach_synthesis",
            lambda pkt: pkt.update(
                {
                    "compiled_synthesis": "synth10",
                    "opportunity_analysis": "synth11",
                    "report_summary": "synth12",
                }
            ),
        )
        main(
            [
                Arg.DATA_DIR,
                str(tmp_path),
                "research",
                "youtube",
                "AI",
                "latest-news",
                Arg.NO_HTML,
            ]
        )
        out = capsys.readouterr().out.strip()
        # --no-html falls back to Markdown report
        assert out.endswith(".md")

    def test_runner_none_emits_packet_without_sections_10_12(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setattr(
            "social_research_probe.pipeline.run_pipeline",
            AsyncMock(return_value=copy.deepcopy(_VALID_PACKET)),
        )
        monkeypatch.setattr("social_research_probe.cli._attach_synthesis", lambda pkt: None)
        main(
            [
                Arg.DATA_DIR,
                str(tmp_path),
                "research",
                "youtube",
                "AI",
                "latest-news",
                Arg.NO_HTML,
            ]
        )
        out = capsys.readouterr().out.strip()
        assert out.endswith(".md")


class TestResearchPreflightWarning:
    """Covers the runner-not-found pre-flight log in the research command."""

    def test_runner_binary_not_found_logs_warning(self, monkeypatch, tmp_path):
        """research still succeeds when the configured runner binary is missing."""

        class _Cfg:
            default_structured_runner = "claude"

        class _UnhealthyRunner:
            def health_check(self) -> bool:
                return False

        monkeypatch.setattr("social_research_probe.cli.load_active_config", lambda: _Cfg())
        monkeypatch.setattr("social_research_probe.cli.get_runner", lambda name: _UnhealthyRunner())
        monkeypatch.setattr(
            "social_research_probe.pipeline.run_pipeline",
            AsyncMock(return_value=copy.deepcopy(_VALID_PACKET)),
        )
        monkeypatch.setattr("social_research_probe.cli._attach_synthesis", lambda pkt: None)
        result = main([Arg.DATA_DIR, str(tmp_path), "research", "ai", "latest-news", Arg.NO_HTML])
        assert result == 0

    def test_llm_service_disabled_skips_runner_preflight(self, monkeypatch, tmp_path):
        class _Cfg:
            default_structured_runner = "claude"

            def service_enabled(self, name: str) -> bool:
                return name != "llm"

        monkeypatch.setattr("social_research_probe.cli.load_active_config", lambda: _Cfg())
        monkeypatch.setattr(
            "social_research_probe.pipeline.run_pipeline",
            AsyncMock(return_value=copy.deepcopy(_VALID_PACKET)),
        )
        monkeypatch.setattr("social_research_probe.cli._attach_synthesis", lambda pkt: None)
        result = main([Arg.DATA_DIR, str(tmp_path), "research", "ai", "latest-news", Arg.NO_HTML])
        assert result == 0

    def test_runner_binary_found_no_warning(self, monkeypatch, tmp_path):
        """research succeeds and emits no warning when runner binary is on PATH."""

        class _Cfg:
            default_structured_runner = "claude"

        class _HealthyRunner:
            def health_check(self) -> bool:
                return True

        monkeypatch.setattr("social_research_probe.cli.load_active_config", lambda: _Cfg())
        monkeypatch.setattr("social_research_probe.cli.get_runner", lambda name: _HealthyRunner())
        monkeypatch.setattr(
            "social_research_probe.pipeline.run_pipeline",
            AsyncMock(return_value=copy.deepcopy(_VALID_PACKET)),
        )
        monkeypatch.setattr("social_research_probe.cli._attach_synthesis", lambda pkt: None)
        result = main([Arg.DATA_DIR, str(tmp_path), "research", "ai", "latest-news", Arg.NO_HTML])
        assert result == 0

    def test_multi_packet_html_falls_back_to_markdown(self, monkeypatch, tmp_path, capsys):
        """Multi-topic packets cannot render HTML — fall back to Markdown stub."""
        multi = {**_VALID_PACKET, "multi": [_VALID_PACKET]}
        monkeypatch.setattr(
            "social_research_probe.pipeline.run_pipeline",
            AsyncMock(return_value=copy.deepcopy(multi)),
        )
        monkeypatch.setattr("social_research_probe.cli._attach_synthesis", lambda pkt: None)
        result = main([Arg.DATA_DIR, str(tmp_path), "research", "ai", "latest-news"])
        assert result == 0
        out = capsys.readouterr().out.strip()
        assert out.endswith(".md")


class TestAttachSynthesis:
    """Covers _attach_synthesis and _structured_runner_order branches."""

    def test_attach_synthesis_multi_children_path(self, monkeypatch):
        """_attach_synthesis iterates children when packet has a 'multi' list."""
        from social_research_probe.commands.research import _attach_synthesis

        synth = {
            "compiled_synthesis": "compiled synthesis",
            "opportunity_analysis": "opportunity analysis",
            "report_summary": "final summary",
        }
        monkeypatch.setattr("social_research_probe.cli._run_required_synthesis", lambda pkt: synth)
        packet = {"multi": [{"topic": "a"}, {"topic": "b"}]}
        _attach_synthesis(packet)
        for child in packet["multi"]:
            assert child["compiled_synthesis"] == "compiled synthesis"
            assert child["report_summary"] == "final summary"

    def test_attach_synthesis_multi_child_synthesis_none_skips_update(self, monkeypatch):
        """_attach_synthesis skips update for children when synthesis returns None."""
        from social_research_probe.commands.research import _attach_synthesis

        monkeypatch.setattr("social_research_probe.cli._run_required_synthesis", lambda pkt: None)
        packet = {"multi": [{"topic": "a"}]}
        _attach_synthesis(packet)
        assert "compiled_synthesis" not in packet["multi"][0]

    def test_attach_synthesis_single_packet_updates_when_synthesis_not_none(self, monkeypatch):
        """_attach_synthesis merges synthesis into the packet when synthesis is returned."""
        from social_research_probe.commands.research import _attach_synthesis

        synth = {
            "compiled_synthesis": "compiled synthesis",
            "opportunity_analysis": "opportunity analysis",
            "report_summary": "final summary",
        }
        monkeypatch.setattr("social_research_probe.cli._run_required_synthesis", lambda pkt: synth)
        packet = {"topic": "ai"}
        _attach_synthesis(packet)
        assert packet["compiled_synthesis"] == "compiled synthesis"
        assert packet["report_summary"] == "final summary"

    def test_attach_synthesis_single_packet_synthesis_none_no_update(self, monkeypatch):
        """_attach_synthesis leaves the packet unchanged when synthesis returns None."""
        from social_research_probe.commands.research import _attach_synthesis

        monkeypatch.setattr("social_research_probe.cli._run_required_synthesis", lambda pkt: None)
        packet = {"topic": "ai"}
        _attach_synthesis(packet)
        assert "compiled_synthesis" not in packet

    def test_structured_runner_order_none_returns_empty(self):
        """_structured_runner_order returns [] when preferred is 'none'."""
        from social_research_probe.commands.research import _structured_runner_order

        assert _structured_runner_order("none") == []

    def test_run_required_synthesis_validation_error_is_caught(self, monkeypatch):
        """ValidationError from parse_synthesis_response is caught and logged."""
        from social_research_probe.errors import ValidationError

        from social_research_probe.commands.research import _run_required_synthesis

        class _Cfg:
            default_structured_runner = "claude"

        class _Runner:
            def health_check(self) -> bool:
                return True

            def run(self, prompt, *, schema=None):
                raise ValidationError("bad synthesis")

        monkeypatch.setattr("social_research_probe.cli.load_active_config", lambda: _Cfg())
        monkeypatch.setattr("social_research_probe.cli.get_runner", lambda name: _Runner())
        assert _run_required_synthesis(_VALID_PACKET) is None
