"""srp config subcommand: set/get/check for non-secret and secret values."""
from __future__ import annotations

import json
import os
import stat
from pathlib import Path

import pytest

from social_research_probe.commands.config import (
    SECRET_FILENAME,
    check_secrets,
    mask_secret,
    read_secret,
    show_config,
    unset_secret,
    write_config_value,
    write_secret,
)


def test_write_and_read_secret(tmp_data_dir: Path):
    write_secret(tmp_data_dir, "youtube_api_key", "AIzaTESTVALUE123")
    assert read_secret(tmp_data_dir, "youtube_api_key") == "AIzaTESTVALUE123"


def test_secret_file_has_0600_perms(tmp_data_dir: Path):
    write_secret(tmp_data_dir, "youtube_api_key", "x")
    path = tmp_data_dir / SECRET_FILENAME
    mode = stat.S_IMODE(path.stat().st_mode)
    assert mode == 0o600, f"expected 0600, got {oct(mode)}"


def test_env_var_overrides_file(tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch):
    write_secret(tmp_data_dir, "youtube_api_key", "from-file")
    monkeypatch.setenv("SRP_YOUTUBE_API_KEY", "from-env")
    assert read_secret(tmp_data_dir, "youtube_api_key") == "from-env"


def test_unset_secret_removes(tmp_data_dir: Path):
    write_secret(tmp_data_dir, "youtube_api_key", "x")
    unset_secret(tmp_data_dir, "youtube_api_key")
    assert read_secret(tmp_data_dir, "youtube_api_key") is None


def test_mask_secret_short():
    assert mask_secret("abc") == "***"


def test_mask_secret_long():
    assert mask_secret("abcdef1234567890") == "abcd...7890"


def test_show_config_masks_secrets(tmp_data_dir: Path):
    write_secret(tmp_data_dir, "youtube_api_key", "AIzaTESTLONGVALUE")
    out = show_config(tmp_data_dir)
    assert "AIzaTESTLONGVALUE" not in out
    assert "..." in out  # masked
    assert "youtube_api_key" in out


def test_check_secrets_structure(tmp_data_dir: Path):
    result = check_secrets(
        tmp_data_dir,
        needed_for="run-research",
        platform="youtube",
        corroboration=None,
    )
    assert set(result.keys()) == {"required", "optional", "present", "missing"}
    assert "youtube_api_key" in result["required"]
    assert "youtube_api_key" in result["missing"]


def test_check_secrets_detects_present(tmp_data_dir: Path):
    write_secret(tmp_data_dir, "youtube_api_key", "x")
    result = check_secrets(
        tmp_data_dir,
        needed_for="run-research",
        platform="youtube",
        corroboration=None,
    )
    assert "youtube_api_key" in result["present"]
    assert result["missing"] == []


def test_write_config_value(tmp_data_dir: Path):
    write_config_value(tmp_data_dir, "llm.runner", "claude")
    content = (tmp_data_dir / "config.toml").read_text()
    assert 'runner = "claude"' in content


def test_check_perms_warns_on_bad_perms(tmp_data_dir: Path, capsys):
    """Lines 46-47: _check_perms prints warning when permissions are too open."""
    import os
    import stat as stat_mod
    from social_research_probe.commands.config import _check_perms

    path = tmp_data_dir / "secrets.toml"
    path.write_text("[secrets]\n")
    os.chmod(path, 0o644)  # too open
    _check_perms(path)
    err = capsys.readouterr().err
    assert "warning" in err
    assert "0600" in err


def test_show_config_env_var_shown(tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch):
    """Line 110: show_config shows env-sourced secret with (from env) label."""
    write_secret(tmp_data_dir, "youtube_api_key", "from-file-val")
    monkeypatch.setenv("SRP_YOUTUBE_API_KEY", "envkeyvalue123")
    out = show_config(tmp_data_dir)
    assert "from env" in out
    assert "enva...e123" in out or "envk...e123" in out or "envk" in out


def test_write_config_value_bad_key_raises():
    """Line 119: write_config_value raises when key is not section.key format."""
    from pathlib import Path
    from social_research_probe.errors import ValidationError
    with pytest.raises(ValidationError, match="section.key"):
        write_config_value(Path("/tmp"), "badkey", "value")


def test_write_config_value_reads_existing(tmp_data_dir: Path):
    """Lines 125-126: write_config_value reads existing config file before updating."""
    # Write an initial config
    write_config_value(tmp_data_dir, "llm.runner", "openai")
    # Now update a different key — existing content should be preserved
    write_config_value(tmp_data_dir, "llm.model", "gpt-4")
    content = (tmp_data_dir / "config.toml").read_text()
    assert 'runner = "openai"' in content
    assert 'model = "gpt-4"' in content


def test_write_config_value_bool_value(tmp_data_dir: Path):
    """Lines 136-139: write_config_value writes bool values as true/false."""
    # Manually inject a bool into the config by writing a toml that has one
    cfg_path = tmp_data_dir / "config.toml"
    cfg_path.write_text('[llm]\nenabled = true\n')
    # Now write another value — existing bool should survive round-trip
    write_config_value(tmp_data_dir, "llm.runner", "claude")
    content = cfg_path.read_text()
    assert "enabled = true" in content
    assert 'runner = "claude"' in content


def test_check_secrets_corroboration_branch(tmp_data_dir: Path):
    """Line 156: check_secrets processes corroboration secrets."""
    result = check_secrets(
        tmp_data_dir,
        needed_for=None,
        platform=None,
        corroboration="exa",
    )
    assert "exa_api_key" in result["required"]
    assert "exa_api_key" in result["missing"]


def test_check_secrets_no_needed_for_skips_platform(tmp_data_dir: Path):
    """Branch 153->155: needed_for != 'run-research' skips platform secrets."""
    result = check_secrets(
        tmp_data_dir,
        needed_for="something-else",
        platform="youtube",
        corroboration=None,
    )
    # youtube_api_key should NOT be required since needed_for isn't run-research
    assert "youtube_api_key" not in result["required"]


def test_write_config_value_numeric_value(tmp_data_dir: Path):
    """Lines 138-139: write_config_value writes non-bool non-str values as bare literals."""
    cfg_path = tmp_data_dir / "config.toml"
    cfg_path.write_text('[limits]\nmax_items = 20\n')
    write_config_value(tmp_data_dir, "limits.timeout", "30")
    content = cfg_path.read_text()
    assert "max_items = 20" in content
