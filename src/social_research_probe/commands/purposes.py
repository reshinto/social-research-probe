"""Purposes CRUD."""
from __future__ import annotations

from pathlib import Path

from social_research_probe.dedupe import DuplicateStatus, classify
from social_research_probe.errors import DuplicateError, ValidationError
from social_research_probe.purposes import registry


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
    if result.status is not DuplicateStatus.NEW and not force:
        raise DuplicateError(
            f"purpose {name!r} {result.status.value} with {result.matches} (use --force to override)"
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
        return
    data["purposes"][new] = data["purposes"].pop(old)
    registry.save(data_dir, data)
