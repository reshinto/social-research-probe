"""Extra coverage for purposes/registry.py — the get() function (lines 28-31)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from social_research_probe.purposes.registry import get


def _write_purposes(tmp_path: Path, purposes: dict) -> None:
    data = {
        "schema_version": 1,
        "purposes": purposes,
    }
    (tmp_path / "purposes.json").write_text(json.dumps(data), encoding="utf-8")


def test_get_existing_purpose(tmp_path):
    _write_purposes(
        tmp_path,
        {
            "latest-news": {
                "method": "Track latest channels for breaking news",
                "evidence_priorities": [],
            }
        },
    )
    result = get(tmp_path, "latest-news")
    assert result["method"] == "Track latest channels for breaking news"


def test_get_missing_purpose_raises_key_error(tmp_path):
    _write_purposes(
        tmp_path,
        {
            "latest-news": {
                "method": "Track latest channels",
                "evidence_priorities": [],
            }
        },
    )
    with pytest.raises(KeyError):
        get(tmp_path, "nonexistent")
