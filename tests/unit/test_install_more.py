"""More install_skill tests."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from social_research_probe.commands import install_skill
from social_research_probe.utils.core.errors import ValidationError


@pytest.fixture
def isolated(tmp_path):
    cfg = MagicMock()
    cfg.data_dir = tmp_path
    cfg.voicebox = {"api_base": "http://x"}
    with patch("social_research_probe.config.load_active_config", return_value=cfg):
        yield tmp_path


def test_install_cli_uv(monkeypatch, capsys):
    monkeypatch.setattr(install_skill.shutil, "which", lambda b: "/uv" if b == "uv" else None)
    called = {}

    def fake_run(cmd, check):
        called["cmd"] = cmd

    monkeypatch.setattr(install_skill.subprocess, "run", fake_run)
    install_skill._install_cli()
    assert "uv" in called["cmd"]


def test_install_cli_pipx(monkeypatch):
    monkeypatch.setattr(install_skill.shutil, "which", lambda b: "/pipx" if b == "pipx" else None)
    called = {}

    def fake_run(cmd, check):
        called["cmd"] = cmd

    monkeypatch.setattr(install_skill.subprocess, "run", fake_run)
    install_skill._install_cli()
    assert "pipx" in called["cmd"]


def test_install_cli_none(monkeypatch, capsys):
    monkeypatch.setattr(install_skill.shutil, "which", lambda b: None)
    install_skill._install_cli()
    assert "warning" in capsys.readouterr().out


def test_copy_config_example_fresh(isolated, monkeypatch, capsys):
    bundled = isolated / "bundled.toml"
    bundled.write_text('[llm]\nrunner = "none"\n')
    monkeypatch.setattr(install_skill, "_BUNDLED_CONFIG", bundled)
    install_skill._copy_config_example()
    assert (isolated / "config.toml").exists()


def test_copy_config_example_merge(isolated, monkeypatch, capsys):
    bundled = isolated / "bundled.toml"
    bundled.write_text('[llm]\nrunner = "none"\nnewkey = "x"\n')
    monkeypatch.setattr(install_skill, "_BUNDLED_CONFIG", bundled)
    (isolated / "config.toml").write_text('[llm]\nrunner = "claude"\n')
    install_skill._copy_config_example()
    text = (isolated / "config.toml").read_text()
    assert "newkey" in text


def test_load_and_merge_no_added(isolated, monkeypatch):
    bundled = isolated / "b.toml"
    bundled.write_text("[a]\nx = 1\n")
    monkeypatch.setattr(install_skill, "_BUNDLED_CONFIG", bundled)
    target = isolated / "c.toml"
    target.write_text("[a]\nx = 2\n")
    _cfg, added = install_skill._load_and_merge_configs(target)
    assert added == []


def test_deep_merge_missing_nested(isolated):
    target = {"a": {"x": 1}}
    source = {"a": {"y": 2}, "b": 3}
    added: list = []
    install_skill._deep_merge_missing(target, source, (), added)
    assert "a.y" in added and "b" in added


def test_get_runner_choice_skip_kbd(capsys):
    def kbd(p):
        raise KeyboardInterrupt

    assert install_skill._get_runner_choice(_input=kbd) is None


def test_write_runner_config_none(monkeypatch, capsys):
    called = []
    monkeypatch.setattr(
        "social_research_probe.commands.config.write_config_value",
        lambda k, v: called.append((k, v)),
    )
    install_skill._write_runner_config("none")
    assert called == [("llm.runner", "none")]


def test_write_runner_config_named(monkeypatch, capsys):
    called = []
    monkeypatch.setattr(
        "social_research_probe.commands.config.write_config_value",
        lambda k, v: called.append((k, v)),
    )
    install_skill._write_runner_config("claude")
    assert ("technologies.claude", "true") in called


def test_prompt_for_runner_chosen(monkeypatch):
    monkeypatch.setattr(install_skill, "_get_runner_choice", lambda **kw: "claude")
    called = []
    monkeypatch.setattr(install_skill, "_write_runner_config", lambda r: called.append(r))
    install_skill._prompt_for_runner()
    assert called == ["claude"]


def test_prompt_for_runner_none(monkeypatch):
    monkeypatch.setattr(install_skill, "_get_runner_choice", lambda **kw: None)
    install_skill._prompt_for_runner()


def test_prompt_for_single_secret_value(isolated):
    with patch("social_research_probe.commands.config.read_secret", return_value="existing"):
        val, cont = install_skill._prompt_for_single_secret(
            "n", "d", "url", _input=lambda p: "newvalue"
        )
    assert val == "newvalue" and cont is True


def test_prompt_for_secrets_runs(isolated, monkeypatch, capsys):
    monkeypatch.setattr(install_skill, "_KEY_PROMPTS", [("k", "d", "u")])
    monkeypatch.setattr(
        install_skill,
        "_prompt_for_single_secret",
        lambda *a, **kw: ("value", True),
    )
    written = {}
    monkeypatch.setattr(
        "social_research_probe.commands.config.write_secret",
        lambda n, v: written.update({n: v}),
    )
    install_skill._prompt_for_secrets()
    assert written == {"k": "value"}


def test_prompt_for_secrets_eof(isolated, monkeypatch, capsys):
    monkeypatch.setattr(install_skill, "_KEY_PROMPTS", [("k", "d", "u"), ("k2", "d", "u")])
    monkeypatch.setattr(
        install_skill,
        "_prompt_for_single_secret",
        lambda *a, **kw: (None, False),
    )
    install_skill._prompt_for_secrets()


def test_get_voicebox_default_url(isolated):
    assert install_skill._get_voicebox_default_url() == "http://x"


def test_ensure_voicebox_secrets_when_missing(isolated, monkeypatch):
    written = {}
    monkeypatch.setattr(
        "social_research_probe.commands.config.read_secret",
        lambda n: None,
    )
    monkeypatch.setattr(
        "social_research_probe.commands.config.write_secret",
        lambda n, v: written.update({n: v}),
    )
    install_skill._ensure_voicebox_secrets()
    assert "tts_voicebox_server_url" in written


def test_ensure_voicebox_secrets_when_present(isolated, monkeypatch):
    monkeypatch.setattr(
        "social_research_probe.commands.config.read_secret",
        lambda n: "set",
    )
    written = {}
    monkeypatch.setattr(
        "social_research_probe.commands.config.write_secret",
        lambda n, v: written.update({n: v}),
    )
    install_skill._ensure_voicebox_secrets()
    assert written == {}


def test_run_full_flow(isolated, monkeypatch, capsys):
    monkeypatch.setattr(install_skill, "_install_cli", lambda: None)
    monkeypatch.setattr(install_skill, "_copy_config_example", lambda: None)
    monkeypatch.setattr(install_skill, "_prompt_for_secrets", lambda: None)
    monkeypatch.setattr(install_skill, "_ensure_voicebox_secrets", lambda: None)
    monkeypatch.setattr(install_skill, "_prompt_for_runner", lambda: None)
    monkeypatch.setattr(install_skill.shutil, "copytree", lambda s, d: None)
    monkeypatch.setattr(install_skill.shutil, "rmtree", lambda d: None)
    target = Path.home() / ".claude" / "skills" / "srp_test_install_unique"
    rc = install_skill.run(str(target))
    assert rc == 0


def test_run_invalid_target(isolated):
    with pytest.raises(ValidationError):
        install_skill.run("/tmp/outside-claude-test-only")
