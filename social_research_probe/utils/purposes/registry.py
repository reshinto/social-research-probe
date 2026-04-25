"""Purpose lookup + persistence helpers (read/write purposes.json)."""

from __future__ import annotations

from typing import cast

from social_research_probe.utils.core.types import JSONObject, PurposeEntry, PurposesState
from social_research_probe.utils.state.migrate import migrate_to_current
from social_research_probe.utils.state.schemas import PURPOSES_SCHEMA, default_purposes
from social_research_probe.utils.state.store import atomic_write_json, read_json
from social_research_probe.utils.state.validate import validate

_FILENAME = "purposes.json"


def load() -> PurposesState:
    """Load, migrate, validate, and return purposes.json."""
    from social_research_probe.config import load_active_config

    data_dir = load_active_config().data_dir
    path = data_dir / _FILENAME
    data = read_json(path, default_factory=default_purposes)
    data = cast(PurposesState, migrate_to_current(path, cast(JSONObject, data), kind="purposes"))
    validate(data, PURPOSES_SCHEMA)
    return data


def save(data: PurposesState) -> None:
    """Validate and persist purposes.json atomically."""
    from social_research_probe.config import load_active_config

    data_dir = load_active_config().data_dir
    validate(data, PURPOSES_SCHEMA)
    atomic_write_json(data_dir / _FILENAME, data)


def get(name: str) -> PurposeEntry:
    """Return one purpose entry by name."""
    data = load()
    if name not in data["purposes"]:
        raise KeyError(name)
    return dict(data["purposes"][name])
