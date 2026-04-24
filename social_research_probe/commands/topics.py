"""Topics CRUD. Reads/writes topics.json through state.store, dedupes via dedupe.classify."""

from __future__ import annotations

import argparse
from pathlib import Path

from social_research_probe.utils.core.dedupe import DuplicateStatus, classify
from social_research_probe.utils.core.errors import DuplicateError
from social_research_probe.utils.state.migrate import migrate_to_current
from social_research_probe.utils.state.schemas import TOPICS_SCHEMA, default_topics
from social_research_probe.utils.state.store import atomic_write_json, read_json
from social_research_probe.utils.state.validate import validate

_FILENAME = "topics.json"


def _load(data_dir: Path) -> dict:
    path = data_dir / _FILENAME
    data = read_json(path, default_factory=default_topics)
    data = migrate_to_current(path, data, kind="topics")
    validate(data, TOPICS_SCHEMA)
    return data


def _save(data_dir: Path, data: dict) -> None:
    topics = data["topics"]
    if len(topics) != len(set(topics)):
        raise DuplicateError("internal error: attempted to save duplicate topics")
    data["topics"] = sorted(topics)
    validate(data, TOPICS_SCHEMA)
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
        else:
            conflicts.append((value, result.matches))

    if conflicts and not force:
        descriptions = "; ".join(f"{v!r} ~ {m}" for v, m in conflicts)
        raise DuplicateError(
            f"duplicate/near-duplicate topics: {descriptions} (use --force to override)"
        )

    seen = set(existing)
    deduped_to_add = []
    for v in to_add:
        if v not in seen:
            deduped_to_add.append(v)
            seen.add(v)

    data["topics"] = existing + deduped_to_add
    _save(data_dir, data)


def remove_topics(data_dir: Path, values: list[str]) -> None:
    data = _load(data_dir)
    remove_set = set(values)
    data["topics"] = [t for t in data["topics"] if t not in remove_set]
    _save(data_dir, data)


def rename_topic(data_dir: Path, old: str, new: str) -> None:
    data = _load(data_dir)
    existing = list(data["topics"])
    if old not in existing:
        from social_research_probe.utils.core.errors import SrpError

        raise SrpError(f"topic {old!r} not found")
    if new in existing:
        raise DuplicateError(f"{new!r} already exists; rename would cause a duplicate")
    data["topics"] = [new if t == old else t for t in existing]
    _save(data_dir, data)


def run_update(args: argparse.Namespace, data_dir: Path) -> int:
    from social_research_probe.cli.utils import _emit
    from social_research_probe.commands.parse import _parse_quoted_list, _take_quoted
    from social_research_probe.utils.core.errors import ValidationError

    if args.add:
        add_topics(data_dir, _parse_quoted_list(args.add), force=args.force)
    elif args.remove:
        remove_topics(data_dir, _parse_quoted_list(args.remove))
    else:
        old, pos = _take_quoted(args.rename, 0)
        if args.rename[pos : pos + 2] != "->":
            raise ValidationError("rename expects old->new")
        new, _ = _take_quoted(args.rename, pos + 2)
        rename_topic(data_dir, old, new)
    _emit({"ok": True}, args.output)
    return 0


def run_show(args: argparse.Namespace, data_dir: Path) -> int:
    from social_research_probe.cli.utils import _emit

    _emit({"topics": show_topics(data_dir)}, args.output)
    return 0
