"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def tmp_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect SRP data dir to a per-test temp path."""
    data_dir = tmp_path / ".skill-data"
    data_dir.mkdir(exist_ok=True)
    monkeypatch.setenv("SRP_DATA_DIR", str(data_dir))
    return data_dir
