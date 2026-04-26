"""Tests for utils.purposes.registry."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from social_research_probe.utils.purposes import registry


@pytest.fixture
def isolated_data_dir(tmp_path: Path):
    cfg = MagicMock()
    cfg.data_dir = tmp_path
    with patch("social_research_probe.config.load_active_config", return_value=cfg):
        yield tmp_path


def test_load_seeds_default(isolated_data_dir: Path):
    data = registry.load()
    assert data["purposes"] == {}
    assert (isolated_data_dir / "purposes.json").exists()


def test_save_then_load_roundtrip(isolated_data_dir: Path):
    payload = {
        "schema_version": 1,
        "purposes": {"career": {"method": "M", "evidence_priorities": []}},
    }
    registry.save(payload)
    loaded = registry.load()
    assert loaded["purposes"]["career"]["method"] == "M"


def test_get_existing(isolated_data_dir: Path):
    payload = {
        "schema_version": 1,
        "purposes": {"career": {"method": "M", "evidence_priorities": ["x"]}},
    }
    registry.save(payload)
    entry = registry.get("career")
    assert entry["method"] == "M"


def test_get_missing_raises_keyerror(isolated_data_dir: Path):
    with pytest.raises(KeyError):
        registry.get("absent")
