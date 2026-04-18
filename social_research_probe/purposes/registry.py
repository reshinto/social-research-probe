"""Purpose lookup + persistence helpers (read/write purposes.json)."""
from __future__ import annotations

from pathlib import Path

from social_research_probe.state.migrate import migrate_to_current
from social_research_probe.state.schemas import PURPOSES_SCHEMA, default_purposes
from social_research_probe.state.store import atomic_write_json, read_json
from social_research_probe.state.validate import validate

_FILENAME = "purposes.json"


def load(data_dir: Path) -> dict:
    path = data_dir / _FILENAME
    data = read_json(path, default_factory=default_purposes)
    data = migrate_to_current(path, data, kind="purposes")
    validate(data, PURPOSES_SCHEMA)
    return data


def save(data_dir: Path, data: dict) -> None:
    validate(data, PURPOSES_SCHEMA)
    atomic_write_json(data_dir / _FILENAME, data)


def get(data_dir: Path, name: str) -> dict:
    data = load(data_dir)
    if name not in data["purposes"]:
        raise KeyError(name)
    return dict(data["purposes"][name])
