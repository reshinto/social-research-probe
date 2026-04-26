"""Tests for commands.config module."""

from __future__ import annotations

import argparse
import os
import stat
import tomllib
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from social_research_probe.commands import ConfigSubcommand
from social_research_probe.commands import config as cfg_cmd
from social_research_probe.utils.core.errors import ValidationError


@pytest.fixture
def isolated_data_dir(tmp_path: Path):
    cfg = MagicMock()
    cfg.data_dir = tmp_path
    cfg.raw = {"section": {"k": 1}}
    with patch("social_research_probe.config.load_active_config", return_value=cfg):
        yield tmp_path


def test_env_key():
    assert cfg_cmd._env_key("foo") == "SRP_FOO"


def test_mask_secret_short():
    assert cfg_cmd.mask_secret("abc") == "***"


def test_mask_secret_long():
    out = cfg_cmd.mask_secret("abcd1234efgh")
    assert "abcd" in out and "efgh" in out


def test_format_toml_value_string():
    assert cfg_cmd._format_toml_value("hello") == '"hello"'


def test_format_toml_value_string_escapes():
    assert cfg_cmd._format_toml_value('a"b') == '"a\\"b"'


def test_format_toml_value_bool():
    assert cfg_cmd._format_toml_value(True) == "true"
    assert cfg_cmd._format_toml_value(False) == "false"


def test_format_toml_value_numeric():
    assert cfg_cmd._format_toml_value(5) == "5"
    assert cfg_cmd._format_toml_value(1.5) == "1.5"


def test_format_toml_value_list():
    assert cfg_cmd._format_toml_value([1, "x"]) == '[1, "x"]'


def test_format_toml_value_unsupported():
    with pytest.raises(ValidationError):
        cfg_cmd._format_toml_value(object())


def test_parse_scalar_value():
    assert cfg_cmd._parse_scalar_value("true") is True
    assert cfg_cmd._parse_scalar_value("false") is False
    assert cfg_cmd._parse_scalar_value("42") == 42
    assert cfg_cmd._parse_scalar_value("3.14") == 3.14
    assert cfg_cmd._parse_scalar_value("abc") == "abc"


def test_set_nested_value_creates_path():
    config: dict = {}
    cfg_cmd._set_nested_value(config, ["a", "b", "c"], 1)
    assert config == {"a": {"b": {"c": 1}}}


def test_set_nested_value_overwrites_non_dict():
    config = {"a": "scalar"}
    cfg_cmd._set_nested_value(config, ["a", "b"], 1)
    assert config == {"a": {"b": 1}}


def test_prepare_config_update_invalid_key():
    with pytest.raises(ValidationError):
        cfg_cmd._prepare_config_update("solo", "x", {})


def test_secrets_roundtrip(isolated_data_dir, monkeypatch):
    monkeypatch.delenv("SRP_API_KEY", raising=False)
    cfg_cmd.write_secret("api_key", "sek")
    assert cfg_cmd.read_secret("api_key") == "sek"
    cfg_cmd.unset_secret("api_key")
    assert cfg_cmd.read_secret("api_key") is None


def test_read_secret_env_overrides(isolated_data_dir, monkeypatch):
    cfg_cmd.write_secret("k1", "fileval")
    monkeypatch.setenv("SRP_K1", "envval")
    assert cfg_cmd.read_secret("k1") == "envval"


def test_secrets_file_perms(isolated_data_dir):
    cfg_cmd.write_secret("k", "v")
    path = isolated_data_dir / "secrets.toml"
    mode = stat.S_IMODE(os.stat(path).st_mode)
    assert mode == 0o600


def test_check_perms_warns_on_bad(isolated_data_dir, capsys):
    path = isolated_data_dir / "secrets.toml"
    path.write_text("[secrets]\n")
    os.chmod(path, 0o644)
    cfg_cmd._check_perms(path)
    err = capsys.readouterr().err
    assert "warning" in err and "0o600" in err


def test_format_secrets_toml():
    out = cfg_cmd._format_secrets_toml({"a": "v1", "b": "v2"})
    assert "[secrets]" in out
    assert 'a = "v1"' in out


def test_show_config(isolated_data_dir):
    out = cfg_cmd.show_config()
    assert "data_dir" in out
    assert "[config]" in out


def test_check_secrets_basic(isolated_data_dir, monkeypatch):
    monkeypatch.delenv("SRP_YOUTUBE_API_KEY", raising=False)
    monkeypatch.delenv("SRP_EXA_API_KEY", raising=False)
    from social_research_probe.utils.core.research_command_parser import ResearchCommand

    out = cfg_cmd.check_secrets(
        needed_for=ResearchCommand.RESEARCH, platform="youtube", corroboration="exa"
    )
    assert "youtube_api_key" in out["required"]
    assert "exa_api_key" in out["required"]
    assert "youtube_api_key" in out["missing"]


def test_check_secrets_no_needed_for(isolated_data_dir, monkeypatch):
    monkeypatch.delenv("SRP_YOUTUBE_API_KEY", raising=False)
    out = cfg_cmd.check_secrets(needed_for=None, platform="youtube", corroboration=None)
    assert out["required"] == []


def test_write_config_value(isolated_data_dir):
    with patch.object(cfg_cmd, "DEFAULT_CONFIG", {"section": {"k": 0}}):
        cfg_cmd.write_config_value("section.k", "42")
    with (isolated_data_dir / "config.toml").open("rb") as f:
        data = tomllib.load(f)
    assert data["section"]["k"] == 42


def test_run_show(isolated_data_dir, capsys):
    args = argparse.Namespace(config_cmd=ConfigSubcommand.SHOW)
    rc = cfg_cmd.run(args)
    assert rc == 0
    assert "data_dir" in capsys.readouterr().out


def test_run_path(isolated_data_dir, capsys):
    args = argparse.Namespace(config_cmd=ConfigSubcommand.PATH)
    rc = cfg_cmd.run(args)
    assert rc == 0
    assert "config:" in capsys.readouterr().out


def test_run_unset(isolated_data_dir):
    cfg_cmd.write_secret("k", "v")
    args = argparse.Namespace(config_cmd=ConfigSubcommand.UNSET_SECRET, name="k")
    assert cfg_cmd.run(args) == 0


def test_run_check_secrets(isolated_data_dir, capsys):
    args = argparse.Namespace(
        config_cmd=ConfigSubcommand.CHECK_SECRETS,
        needed_for=None,
        platform=None,
        corroboration=None,
        output="json",
    )
    rc = cfg_cmd.run(args)
    assert rc == 0


def test_run_unknown_returns_error():
    args = argparse.Namespace(config_cmd="unknown")
    assert cfg_cmd.run(args) != 0


def test_run_set_secret_empty_raises(isolated_data_dir):
    args = argparse.Namespace(name="x", from_stdin=True)
    with patch("sys.stdin") as stdin:
        stdin.read.return_value = ""
        with pytest.raises(ValidationError):
            cfg_cmd.run_set_secret(args)


def test_run_set_secret_writes(isolated_data_dir):
    args = argparse.Namespace(name="x", from_stdin=True)
    with patch("sys.stdin") as stdin:
        stdin.read.return_value = "value\n"
        assert cfg_cmd.run_set_secret(args) == 0
    assert cfg_cmd.read_secret("x") == "value"
