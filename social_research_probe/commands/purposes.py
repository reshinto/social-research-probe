"""Purposes CRUD."""

from __future__ import annotations

import argparse
from pathlib import Path

from social_research_probe.utils.core.dedupe import DuplicateStatus, classify
from social_research_probe.utils.core.errors import DuplicateError, SrpError, ValidationError
from social_research_probe.utils.purposes import registry


def show_purposes(data_dir: Path) -> dict:
    data = registry.load(data_dir)
    out = {}
    for name, entry in data["purposes"].items():
        out[name] = {
            "method": entry["method"],
            "evidence_priorities": list(entry.get("evidence_priorities", [])),
            "scoring_overrides": dict(entry.get("scoring_overrides", {})),
        }
    return out


def add_purpose(data_dir: Path, *, name: str, method: str, force: bool) -> None:
    if not method.strip():
        raise ValidationError("purpose method cannot be empty")

    data = registry.load(data_dir)
    existing_names = list(data["purposes"].keys())

    result = classify(name, existing_names)
    if result.status is DuplicateStatus.DUPLICATE and not force:
        raise DuplicateError(
            f"purpose {name!r} {result.status.value} with {result.matches} (use --force to override)"
        )
    if result.status is DuplicateStatus.NEAR_DUPLICATE and not force:
        raise DuplicateError(
            f"purpose {name!r} {result.status.value} with {result.matches} (use --force to override)"
        )
    # Even with force, never silently overwrite an existing entry
    if name in data["purposes"] and force:
        raise DuplicateError(
            f"purpose {name!r} already exists; use rename to update an existing purpose"
        )

    data["purposes"][name] = {
        "method": method,
        "evidence_priorities": [],
        "scoring_overrides": {},
    }
    registry.save(data_dir, data)


def remove_purposes(data_dir: Path, names: list[str]) -> None:
    data = registry.load(data_dir)
    for n in names:
        data["purposes"].pop(n, None)
    registry.save(data_dir, data)


def rename_purpose(data_dir: Path, old: str, new: str) -> None:
    data = registry.load(data_dir)
    if old not in data["purposes"]:
        raise SrpError(f"purpose {old!r} not found")
    if new in data["purposes"]:
        raise DuplicateError(f"{new!r} already exists; rename would overwrite an existing purpose")
    data["purposes"][new] = data["purposes"].pop(old)
    registry.save(data_dir, data)


def run_update(args: argparse.Namespace, data_dir: Path) -> int:
    from social_research_probe.cli.utils import _emit
    from social_research_probe.commands.parse import _take_quoted
    from social_research_probe.utils.core.errors import ValidationError

    if args.add:
        name, pos = _take_quoted(args.add, 0)
        if args.add[pos : pos + 1] != "=":
            raise ValidationError('add expects "name"="method"')
        method, _ = _take_quoted(args.add, pos + 1)
        add_purpose(data_dir, name=name, method=method, force=args.force)
    elif args.remove:
        from social_research_probe.commands.parse import _parse_quoted_list
        remove_purposes(data_dir, _parse_quoted_list(args.remove))
    else:
        old, pos = _take_quoted(args.rename, 0)
        if args.rename[pos : pos + 2] != "->":
            raise ValidationError("rename expects old->new")
        new, _ = _take_quoted(args.rename, pos + 2)
        rename_purpose(data_dir, old, new)
    _emit({"ok": True}, args.output)
    return 0


def run_show(args: argparse.Namespace, data_dir: Path) -> int:
    from social_research_probe.cli.utils import _emit

    _emit({"purposes": show_purposes(data_dir)}, args.output)
    return 0
