"""Topics CRUD. Reads/writes topics.json through state.store, dedupes via dedupe.classify."""
from __future__ import annotations

from pathlib import Path

from social_research_probe.dedupe import DuplicateStatus, classify
from social_research_probe.errors import DuplicateError
from social_research_probe.state.migrate import migrate_to_current
from social_research_probe.state.schemas import TOPICS_SCHEMA, default_topics
from social_research_probe.state.store import atomic_write_json, read_json
from social_research_probe.state.validate import validate

_FILENAME = "topics.json"


def _load(data_dir: Path) -> dict:
    path = data_dir / _FILENAME
    data = read_json(path, default_factory=default_topics)
    data = migrate_to_current(path, data, kind="topics")
    validate(data, TOPICS_SCHEMA)
    return data


def _save(data_dir: Path, data: dict) -> None:
    validate(data, TOPICS_SCHEMA)
    data["topics"] = sorted(set(data["topics"]))
    atomic_write_json(data_dir / _FILENAME, data)


def show_topics(data_dir: Path) -> list[str]:
    return list(_load(data_dir)["topics"])


def add_topics(data_dir: Path, values: list[str], *, force: bool) -> None:
    data = _load(data_dir)
    existing = list(data["topics"])
    to_add: list[str] = []
    conflicts: list[tuple[str, list[str]]] = []

    for value in values:
        result = classify(value, existing + to_add)
        if result.status is DuplicateStatus.NEW or force:
            to_add.append(value)
        elif result.status is DuplicateStatus.DUPLICATE:
            conflicts.append((value, result.matches))
        else:  # near-duplicate
            conflicts.append((value, result.matches))

    if conflicts and not force:
        descriptions = "; ".join(f"{v!r} ~ {m}" for v, m in conflicts)
        raise DuplicateError(f"duplicate/near-duplicate topics: {descriptions} (use --force to override)")

    data["topics"] = existing + to_add
    _save(data_dir, data)


def remove_topics(data_dir: Path, values: list[str]) -> None:
    data = _load(data_dir)
    remove_set = set(values)
    data["topics"] = [t for t in data["topics"] if t not in remove_set]
    _save(data_dir, data)


def rename_topic(data_dir: Path, old: str, new: str) -> None:
    data = _load(data_dir)
    topics = [new if t == old else t for t in data["topics"]]
    data["topics"] = topics
    _save(data_dir, data)
