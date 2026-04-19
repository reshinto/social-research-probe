"""Tests for cli.py — the main argparse entry point.

Tests call main([...]) directly (in-process) with stubbed command modules
so no real file-system or API operations occur.
"""

from __future__ import annotations

import copy
import io
import json

import pytest

from social_research_probe.cli import _emit, _id_selector, main

_VALID_PACKET = {
    "topic": "ai",
    "platform": "youtube",
    "purpose_set": ["latest-news"],
    "items_top5": [],
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
    "platform_signals_summary": "0 items",
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


class TestShowTopics:
    def test_show_topics_text(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setattr(
            "social_research_probe.commands.topics.show_topics", lambda d: ["ai", "blockchain"]
        )
        assert main(["--data-dir", str(tmp_path), "show-topics"]) == 0
        assert "ai" in capsys.readouterr().out

    def test_show_topics_json(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setattr("social_research_probe.commands.topics.show_topics", lambda d: ["ai"])
        main(["--data-dir", str(tmp_path), "show-topics", "--output", "json"])
        out = json.loads(capsys.readouterr().out)
        assert out["topics"] == ["ai"]


class TestUpdateTopics:
    def test_add_topic(self, monkeypatch, tmp_path):
        calls = []
        monkeypatch.setattr(
            "social_research_probe.commands.topics.add_topics", lambda d, v, force: calls.append(v)
        )
        assert main(["--data-dir", str(tmp_path), "update-topics", "--add", '"ai"']) == 0
        assert len(calls) == 1

    def test_remove_topic(self, monkeypatch, tmp_path):
        calls = []
        monkeypatch.setattr(
            "social_research_probe.commands.topics.remove_topics", lambda d, v: calls.append(v)
        )
        assert main(["--data-dir", str(tmp_path), "update-topics", "--remove", '"ai"']) == 0

    def test_rename_topic(self, monkeypatch, tmp_path):
        calls = []
        monkeypatch.setattr(
            "social_research_probe.commands.topics.rename_topic",
            lambda d, o, n: calls.append((o, n)),
        )
        assert main(["--data-dir", str(tmp_path), "update-topics", "--rename", '"old"->"new"']) == 0

    def test_rename_bad_format_raises(self, monkeypatch, tmp_path):
        result = main(["--data-dir", str(tmp_path), "update-topics", "--rename", '"bad"-->"worse"'])
        assert result != 0


class TestShowPurposes:
    def test_show_purposes(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setattr(
            "social_research_probe.commands.purposes.show_purposes",
            lambda d: {"p1": {"method": "m1"}},
        )
        assert main(["--data-dir", str(tmp_path), "show-purposes"]) == 0
        assert "p1" in capsys.readouterr().out


class TestUpdatePurposes:
    def test_add_purpose(self, monkeypatch, tmp_path):
        calls = []
        monkeypatch.setattr(
            "social_research_probe.commands.purposes.add_purpose",
            lambda d, name, method, force: calls.append(name),
        )
        assert (
            main(["--data-dir", str(tmp_path), "update-purposes", "--add", '"name"="method desc"'])
            == 0
        )

    def test_add_purpose_bad_format_raises(self, monkeypatch, tmp_path):
        result = main(["--data-dir", str(tmp_path), "update-purposes", "--add", '"bad"'])
        assert result != 0

    def test_remove_purpose(self, monkeypatch, tmp_path):
        calls = []
        monkeypatch.setattr(
            "social_research_probe.commands.purposes.remove_purposes", lambda d, v: calls.append(v)
        )
        assert main(["--data-dir", str(tmp_path), "update-purposes", "--remove", '"p1"']) == 0

    def test_rename_purpose(self, monkeypatch, tmp_path):
        calls = []
        monkeypatch.setattr(
            "social_research_probe.commands.purposes.rename_purpose",
            lambda d, o, n: calls.append((o, n)),
        )
        assert (
            main(["--data-dir", str(tmp_path), "update-purposes", "--rename", '"old"->"new"']) == 0
        )

    def test_rename_purpose_bad_format_raises(self, monkeypatch, tmp_path):
        result = main(
            ["--data-dir", str(tmp_path), "update-purposes", "--rename", '"bad"--"worse"']
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
        assert main(["--data-dir", str(tmp_path), "suggest-topics"]) == 0


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
        assert main(["--data-dir", str(tmp_path), "suggest-purposes"]) == 0


class TestPending:
    def test_show_pending(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setattr(
            "social_research_probe.commands.suggestions.show_pending",
            lambda d: {"topic_candidates": [], "purpose_candidates": []},
        )
        assert main(["--data-dir", str(tmp_path), "show-pending"]) == 0

    def test_apply_pending(self, monkeypatch, tmp_path):
        calls = []
        monkeypatch.setattr(
            "social_research_probe.commands.suggestions.apply_pending",
            lambda d, topic_ids, purpose_ids: calls.append(1),
        )
        assert main(["--data-dir", str(tmp_path), "apply-pending", "--topics", "all"]) == 0

    def test_discard_pending(self, monkeypatch, tmp_path):
        calls = []
        monkeypatch.setattr(
            "social_research_probe.commands.suggestions.discard_pending",
            lambda d, topic_ids, purpose_ids: calls.append(1),
        )
        assert main(["--data-dir", str(tmp_path), "discard-pending", "--topics", "1,2"]) == 0


class TestStageSuggestions:
    def test_stage_from_stdin(self, monkeypatch, tmp_path):
        payload = json.dumps({"topic_candidates": ["x"], "purpose_candidates": []})
        monkeypatch.setattr("sys.stdin", io.StringIO(payload))
        monkeypatch.setattr(
            "social_research_probe.commands.suggestions.stage_suggestions",
            lambda d, topic_candidates, purpose_candidates: None,
        )
        assert main(["--data-dir", str(tmp_path), "stage-suggestions", "--from-stdin"]) == 0

    def test_stage_without_from_stdin_raises(self, monkeypatch, tmp_path):
        result = main(["--data-dir", str(tmp_path), "stage-suggestions"])
        assert result != 0

    def test_stage_invalid_json_raises(self, monkeypatch, tmp_path):
        monkeypatch.setattr("sys.stdin", io.StringIO("not json"))
        result = main(["--data-dir", str(tmp_path), "stage-suggestions", "--from-stdin"])
        assert result != 0


class TestResearchCommand:
    def test_research(self, monkeypatch, tmp_path, capsys):
        calls = []
        monkeypatch.setattr(
            "social_research_probe.pipeline.run_research",
            lambda cmd, d, adapter_config=None: (
                calls.append(adapter_config) or copy.deepcopy(_VALID_PACKET)
            ),
        )
        monkeypatch.setattr("social_research_probe.cli._attach_synthesis", lambda pkt: None)
        assert (
            main(
                [
                    "--data-dir",
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
        payload = json.loads(capsys.readouterr().out)
        assert payload["kind"] == "synthesis"


class TestInstallSkillTargetValidation:
    def test_install_skill_target_outside_home_raises(self, monkeypatch, tmp_path):
        """install-skill rejects --target paths outside ~/.claude/."""
        monkeypatch.setattr("pathlib.Path.home", classmethod(lambda cls: tmp_path))
        result = main(["install-skill", "--target", "/tmp/dangerous"])
        assert result != 0


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
        result = main(["install-skill", "--target", str(target)])
        assert result == 0


class TestConfig:
    def test_config_show(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setattr(
            "social_research_probe.commands.config.show_config", lambda d: "config output"
        )
        assert main(["--data-dir", str(tmp_path), "config", "show"]) == 0
        assert "config output" in capsys.readouterr().out

    def test_config_path(self, monkeypatch, tmp_path, capsys):
        assert main(["--data-dir", str(tmp_path), "config", "path"]) == 0
        out = capsys.readouterr().out
        assert "config" in out

    def test_config_set(self, monkeypatch, tmp_path):
        calls = []
        monkeypatch.setattr(
            "social_research_probe.commands.config.write_config_value",
            lambda d, k, v: calls.append((k, v)),
        )
        assert main(["--data-dir", str(tmp_path), "config", "set", "key", "value"]) == 0

    def test_config_set_secret_from_stdin(self, monkeypatch, tmp_path):
        monkeypatch.setattr("sys.stdin", io.StringIO("my-secret"))
        calls = []
        monkeypatch.setattr(
            "social_research_probe.commands.config.write_secret", lambda d, n, v: calls.append(v)
        )
        assert (
            main(["--data-dir", str(tmp_path), "config", "set-secret", "my_key", "--from-stdin"])
            == 0
        )

    def test_config_set_secret_empty_raises(self, monkeypatch, tmp_path):
        monkeypatch.setattr("sys.stdin", io.StringIO(""))
        result = main(
            ["--data-dir", str(tmp_path), "config", "set-secret", "my_key", "--from-stdin"]
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

        result = main(["--data-dir", str(tmp_path), "config", "set-secret", "my_key"])
        assert result == 0
        assert calls == ["secret-from-tty"]

    def test_config_unset_secret(self, monkeypatch, tmp_path):
        calls = []
        monkeypatch.setattr(
            "social_research_probe.commands.config.unset_secret", lambda d, n: calls.append(n)
        )
        assert main(["--data-dir", str(tmp_path), "config", "unset-secret", "my_key"]) == 0

    def test_config_check_secrets(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setattr(
            "social_research_probe.commands.config.check_secrets",
            lambda d, needed_for, platform, corroboration: {"missing": []},
        )
        assert (
            main(["--data-dir", str(tmp_path), "config", "check-secrets", "--output", "json"]) == 0
        )

    def test_config_unknown_subcommand_returns_2(self, monkeypatch, tmp_path):
        # config with no subcommand → returns 2
        result = main(["--data-dir", str(tmp_path), "config"])
        assert result == 2


class TestCorroborateClaims:
    def test_corroborate_claims(self, monkeypatch, tmp_path, capsys):
        claims_file = tmp_path / "claims.json"
        claims_file.write_text(
            json.dumps({"claims": [{"text": "AI is growing.", "source_text": "..."}]})
        )
        monkeypatch.setattr(
            "social_research_probe.commands.corroborate_claims.corroborate_claim",
            lambda c, backends: {"claim_text": c.text, "results": []},
        )
        assert (
            main(["--data-dir", str(tmp_path), "corroborate-claims", "--input", str(claims_file)])
            == 0
        )


class TestRender:
    def test_render(self, monkeypatch, tmp_path, capsys):
        from social_research_probe.stats.base import StatResult
        from social_research_probe.viz.base import ChartResult

        packet_file = tmp_path / "packet.json"
        packet_file.write_text(json.dumps({"items_top5": [{"scores": {"overall": 0.75}}]}))
        monkeypatch.setattr(
            "social_research_probe.commands.render.select_and_run",
            lambda d, label: [StatResult("x", 1.0, "caption")],
        )
        monkeypatch.setattr(
            "social_research_probe.commands.render.select_and_render",
            lambda d, label, output_dir: ChartResult("/tmp/x.png", "cap"),
        )
        assert main(["--data-dir", str(tmp_path), "render", "--packet", str(packet_file)]) == 0


class TestSrpErrorHandling:
    def test_srp_error_returns_exit_code(self, monkeypatch, tmp_path):
        from social_research_probe.errors import ValidationError

        monkeypatch.setattr(
            "social_research_probe.commands.topics.show_topics",
            lambda d: (_ for _ in ()).throw(ValidationError("bad")),
        )
        result = main(["--data-dir", str(tmp_path), "show-topics"])
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
        result = main(["install-skill", "--target", str(target)])
        assert result == 0
        assert any("uv" in str(c) for c in calls)
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
        result = main(["install-skill", "--target", str(target)])
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
        result = main(["install-skill", "--target", str(target)])
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
        def fake(cmd, d, adapter_config=None):
            captured.append((cmd, adapter_config))
            return copy.deepcopy(_VALID_PACKET)

        monkeypatch.setattr("social_research_probe.pipeline.run_research", fake)
        monkeypatch.setattr("social_research_probe.cli._attach_synthesis", lambda pkt: None)

    def test_default_platform_is_youtube(self, monkeypatch, tmp_path):
        captured = []
        self._patch_pipeline(monkeypatch, captured)
        assert main(["--data-dir", str(tmp_path), "research", "ai", "latest-news"]) == 0
        cmd, cfg = captured[0]
        assert cmd.platform == "youtube"
        assert cmd.topics == [("ai", ["latest-news"])]
        assert cfg == {"include_shorts": True, "fetch_transcripts": True}

    def test_explicit_platform_positional(self, monkeypatch, tmp_path):
        captured = []
        self._patch_pipeline(monkeypatch, captured)
        main(["--data-dir", str(tmp_path), "research", "youtube", "ai", "latest-news"])
        cmd, _cfg = captured[0]
        assert cmd.platform == "youtube"

    def test_multiple_purposes_comma_separated(self, monkeypatch, tmp_path):
        captured = []
        self._patch_pipeline(monkeypatch, captured)
        main(["--data-dir", str(tmp_path), "research", "ai", "latest-news,trends"])
        cmd, _cfg = captured[0]
        assert cmd.topics == [("ai", ["latest-news", "trends"])]

    def test_no_shorts_flag_disables_shorts(self, monkeypatch, tmp_path):
        captured = []
        self._patch_pipeline(monkeypatch, captured)
        main(["--data-dir", str(tmp_path), "research", "ai", "latest-news", "--no-shorts"])
        _cmd, cfg = captured[0]
        assert cfg == {"include_shorts": False, "fetch_transcripts": True}

    def test_too_few_args_returns_validation_exit_code(self, monkeypatch, tmp_path):
        from social_research_probe.errors import ValidationError

        captured = []
        self._patch_pipeline(monkeypatch, captured)
        assert main(["--data-dir", str(tmp_path), "research", "ai"]) == ValidationError.exit_code

    def test_empty_purpose_arg_returns_validation_exit_code(self, monkeypatch, tmp_path):
        from social_research_probe.errors import ValidationError

        captured = []
        self._patch_pipeline(monkeypatch, captured)
        assert (
            main(["--data-dir", str(tmp_path), "research", "ai", ","]) == ValidationError.exit_code
        )


class TestSimpleResearchTranscripts:
    def _patch_pipeline(self, monkeypatch, captured):
        def fake(cmd, d, adapter_config=None):
            captured.append((cmd, adapter_config))
            return copy.deepcopy(_VALID_PACKET)

        monkeypatch.setattr("social_research_probe.pipeline.run_research", fake)
        monkeypatch.setattr("social_research_probe.cli._attach_synthesis", lambda pkt: None)

    def test_no_transcripts_flag_disables_transcripts(self, monkeypatch, tmp_path):
        captured = []
        self._patch_pipeline(monkeypatch, captured)
        main(["--data-dir", str(tmp_path), "research", "ai", "latest-news", "--no-transcripts"])
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

    def test_copies_example_when_config_absent(self, tmp_path):
        from social_research_probe.commands.install_skill import _copy_config_example

        _copy_config_example(tmp_path)
        assert (tmp_path / "config.toml").exists()

    def test_skips_copy_when_config_exists(self, tmp_path):
        from social_research_probe.commands.install_skill import _copy_config_example

        existing = tmp_path / "config.toml"
        existing.write_text("original", encoding="utf-8")
        _copy_config_example(tmp_path)
        assert existing.read_text(encoding="utf-8") == "original"

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
        assert written == {"llm.runner": "claude"}

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

    def test_returns_none_when_runner_is_none(self, monkeypatch):
        from social_research_probe.cli import _run_required_synthesis

        class _Cfg:
            default_structured_runner = "none"

        monkeypatch.setattr("social_research_probe.cli.load_active_config", lambda: _Cfg())
        assert _run_required_synthesis({}) is None

    def test_returns_synthesis_on_success(self, monkeypatch):
        from social_research_probe.cli import _run_required_synthesis

        class _Cfg:
            default_structured_runner = "claude"

        captured = {}

        class _Runner:
            def health_check(self) -> bool:
                return True

            def run(self, prompt, *, schema=None):
                captured["schema"] = schema
                return {"compiled_synthesis": "s10 text", "opportunity_analysis": "s11 text"}

        monkeypatch.setattr("social_research_probe.cli.load_active_config", lambda: _Cfg())
        monkeypatch.setattr("social_research_probe.cli.get_runner", lambda name: _Runner())
        result = _run_required_synthesis(_VALID_PACKET)
        assert result == {"compiled_synthesis": "s10 text", "opportunity_analysis": "s11 text"}
        assert captured["schema"]["type"] == "object"
        assert set(captured["schema"]["required"]) == {
            "compiled_synthesis",
            "opportunity_analysis",
        }

    def test_raises_synthesis_error_on_runner_exception(self, monkeypatch):
        from social_research_probe.cli import _run_required_synthesis
        from social_research_probe.errors import SynthesisError

        class _Cfg:
            default_structured_runner = "claude"

        monkeypatch.setattr("social_research_probe.cli.load_active_config", lambda: _Cfg())
        monkeypatch.setattr(
            "social_research_probe.cli.get_runner",
            lambda name: (_ for _ in ()).throw(RuntimeError("no cli")),
        )
        with pytest.raises(SynthesisError, match="failed to generate sections 10-11"):
            _run_required_synthesis(_VALID_PACKET)

    def test_raises_synthesis_error_when_runner_is_unavailable(self, monkeypatch):
        from social_research_probe.cli import _run_required_synthesis
        from social_research_probe.errors import SynthesisError

        class _Cfg:
            default_structured_runner = "gemini"

        class _Runner:
            def health_check(self) -> bool:
                return False

        monkeypatch.setattr("social_research_probe.cli.load_active_config", lambda: _Cfg())
        monkeypatch.setattr("social_research_probe.cli.get_runner", lambda name: _Runner())
        with pytest.raises(SynthesisError, match="unavailable"):
            _run_required_synthesis(_VALID_PACKET)

    def test_falls_back_when_preferred_structured_runner_fails(self, monkeypatch):
        from social_research_probe.cli import _run_required_synthesis

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
                return {"compiled_synthesis": "s10 text", "opportunity_analysis": "s11 text"}

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
            "compiled_synthesis": "s10 text",
            "opportunity_analysis": "s11 text",
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
            "social_research_probe.pipeline.run_research",
            lambda cmd, d, adapter_config=None: copy.deepcopy(_VALID_PACKET),
        )
        monkeypatch.setattr(
            "social_research_probe.cli._attach_synthesis",
            lambda pkt: pkt.update(
                {"compiled_synthesis": "synth10", "opportunity_analysis": "synth11"}
            ),
        )
        main(["--data-dir", str(tmp_path), "research", "youtube", "AI", "latest-news"])
        payload = json.loads(capsys.readouterr().out)
        assert payload["kind"] == "synthesis"
        assert payload["packet"]["compiled_synthesis"] == "synth10"
        assert payload["packet"]["opportunity_analysis"] == "synth11"
        assert payload["packet"]["html_report_path"].startswith("file://")

    def test_no_html_still_emits_synthesized_packet(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setattr(
            "social_research_probe.pipeline.run_research",
            lambda cmd, d, adapter_config=None: copy.deepcopy(_VALID_PACKET),
        )
        monkeypatch.setattr(
            "social_research_probe.cli._attach_synthesis",
            lambda pkt: pkt.update(
                {"compiled_synthesis": "synth10", "opportunity_analysis": "synth11"}
            ),
        )
        main(
            [
                "--data-dir",
                str(tmp_path),
                "research",
                "youtube",
                "AI",
                "latest-news",
                "--no-html",
            ]
        )
        payload = json.loads(capsys.readouterr().out)
        assert payload["packet"]["compiled_synthesis"] == "synth10"
        assert payload["packet"]["opportunity_analysis"] == "synth11"
        assert "html_report_path" not in payload["packet"]

    def test_runner_none_emits_packet_without_sections_10_11(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setattr(
            "social_research_probe.pipeline.run_research",
            lambda cmd, d, adapter_config=None: copy.deepcopy(_VALID_PACKET),
        )
        monkeypatch.setattr("social_research_probe.cli._attach_synthesis", lambda pkt: None)
        main(
            [
                "--data-dir",
                str(tmp_path),
                "research",
                "youtube",
                "AI",
                "latest-news",
                "--no-html",
            ]
        )
        payload = json.loads(capsys.readouterr().out)
        assert "compiled_synthesis" not in payload["packet"]
        assert "opportunity_analysis" not in payload["packet"]
