"""Ordered version-chain migrators. Pure functions; backup before overwrite."""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from pathlib import Path

from social_research_probe.utils.core.errors import MigrationError
from social_research_probe.utils.core.types import JSONObject
from social_research_probe.utils.state.schemas import SCHEMA_VERSION

Migrator = Callable[[JSONObject], JSONObject]


def _tag_version_1(data: JSONObject) -> JSONObject:
    """v0 -> v1: stamp schema_version=1 on bare pre-versioned files."""
    out = dict(data)
    out["schema_version"] = 1
    return out


_MIGRATORS: dict[str, list[Migrator]] = {
    "topics": [_tag_version_1],
    "purposes": [_tag_version_1],
    "pending_suggestions": [_tag_version_1],
}


def migrators_for(kind: str) -> list[Migrator]:
    """Return the forward-migration chain for one state-file kind."""
    if kind not in _MIGRATORS:
        raise MigrationError(f"no migrators registered for kind={kind!r}")
    return _MIGRATORS[kind]


def _write_backup(path: Path, data: JSONObject, version: int) -> None:
    """Persist the pre-migration payload before mutating the on-disk file."""
    backup_dir = path.parent / ".backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    ts = int(time.time())
    backup_path = backup_dir / f"{path.stem}.v{version}.{ts}.json"
    backup_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def migrate_to_current(path: Path, data: JSONObject, *, kind: str) -> JSONObject:
    """Run forward migrators until data.schema_version == SCHEMA_VERSION."""
    current = int(data.get("schema_version", 0))
    target = SCHEMA_VERSION

    if current == target:
        return data
    if current > target:
        raise MigrationError(
            f"{path.name} has schema_version={current}, but this build supports {target}"
        )

    chain = migrators_for(kind)
    _write_backup(path, data, current)
    out = data
    for step_idx in range(current, target):
        migrator = chain[step_idx]
        out = migrator(out)
    return out
