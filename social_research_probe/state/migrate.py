"""Ordered version-chain migrators. Pure functions; backup before overwrite."""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from social_research_probe.errors import MigrationError
from social_research_probe.state.schemas import SCHEMA_VERSION

Migrator = Callable[[dict[str, Any]], dict[str, Any]]


def _tag_version_1(data: dict[str, Any]) -> dict[str, Any]:
    """v0 -> v1: stamp schema_version=1 on bare legacy files."""
    out = dict(data)
    out["schema_version"] = 1
    return out


_MIGRATORS: dict[str, list[Migrator]] = {
    "topics": [_tag_version_1],
    "purposes": [_tag_version_1],
    "pending_suggestions": [_tag_version_1],
}


def migrators_for(kind: str) -> list[Migrator]:
    if kind not in _MIGRATORS:
        raise MigrationError(f"no migrators registered for kind={kind!r}")
    return _MIGRATORS[kind]


def _write_backup(path: Path, data: dict[str, Any], version: int) -> None:
    backup_dir = path.parent / ".backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    ts = int(time.time())
    backup_path = backup_dir / f"{path.stem}.v{version}.{ts}.json"
    backup_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def migrate_to_current(path: Path, data: dict[str, Any], *, kind: str) -> dict[str, Any]:
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
