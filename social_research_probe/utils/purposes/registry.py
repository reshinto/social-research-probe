"""Purpose lookup + persistence helpers (read/write purposes.json)."""

from __future__ import annotations

from pathlib import Path
from typing import cast

from social_research_probe.utils.state.migrate import migrate_to_current
from social_research_probe.utils.state.schemas import PURPOSES_SCHEMA, default_purposes
from social_research_probe.utils.state.store import atomic_write_json, read_json
from social_research_probe.utils.state.validate import validate
from social_research_probe.utils.core.types import JSONObject, PurposeEntry, PurposesState

_FILENAME = "purposes.json"


def load(data_dir: Path) -> PurposesState:
    """Load, migrate, validate, and return purposes.json."""
    path = data_dir / _FILENAME
    data = read_json(path, default_factory=default_purposes)
    data = cast(PurposesState, migrate_to_current(path, cast(JSONObject, data), kind="purposes"))
    validate(data, PURPOSES_SCHEMA)
    return data


def save(data_dir: Path, data: PurposesState) -> None:
    """Validate and persist purposes.json atomically."""
    validate(data, PURPOSES_SCHEMA)
    atomic_write_json(data_dir / _FILENAME, data)


def get(data_dir: Path, name: str) -> PurposeEntry:
    """Return one purpose entry by name."""
    data = load(data_dir)
    if name not in data["purposes"]:
        raise KeyError(name)
    return dict(data["purposes"][name])
