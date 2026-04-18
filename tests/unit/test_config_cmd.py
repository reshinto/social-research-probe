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
