"""CLI command implementations."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal, TypeVar, cast

from social_research_probe.utils.core.dedupe import DuplicateStatus, classify
from social_research_probe.utils.core.errors import DuplicateError, ValidationError
from social_research_probe.utils.core.research_command_parser import ResearchCommand
from social_research_probe.utils.core.types import (
    JSONObject,
    PendingPurposeSuggestion,
    PendingSuggestionsState,
    PendingTopicSuggestion,
    PurposeSuggestionCandidate,
    TopicSuggestionCandidate,
)
from social_research_probe.utils.state.migrate import migrate_to_current
from social_research_probe.utils.state.schemas import (
    PENDING_SUGGESTIONS_SCHEMA,
    TOPICS_SCHEMA,
    default_pending_suggestions,
    default_topics,
)
from social_research_probe.utils.state.store import atomic_write_json, read_json
from social_research_probe.utils.state.validate import validate


class Command(StrEnum):
    """Top-level CLI command names dispatched via handlers_factory.

    Each enum member maps to the exact command string accepted by the CLI.
    Example:
        Use command constants when registering handlers:
        ```python
        handlers = {
            Command.UPDATE_TOPICS: handle_update_topics,
            Command.SHOW_TOPICS: handle_show_topics,
        }
        ```
    """

    UPDATE_TOPICS = "update-topics"
    SHOW_TOPICS = "show-topics"
    UPDATE_PURPOSES = "update-purposes"
    SHOW_PURPOSES = "show-purposes"
    SUGGEST_TOPICS = "suggest-topics"
    SUGGEST_PURPOSES = "suggest-purposes"
    SHOW_PENDING = "show-pending"
    APPLY_PENDING = "apply-pending"
    DISCARD_PENDING = "discard-pending"
    STAGE_SUGGESTIONS = "stage-suggestions"
    RESEARCH = "research"
    CORROBORATE_CLAIMS = "corroborate-claims"
    RENDER = "render"
    INSTALL_SKILL = "install-skill"
    SETUP = "setup"
    REPORT = "report"
    SERVE_REPORT = "serve-report"
    CONFIG = "config"


class ConfigSubcommand(StrEnum):
    """Config subcommand names dispatched within config.run().

    These are not top-level commands; they are sub-actions under the CONFIG command.
    """

    SHOW = "show"
    PATH = "path"
    SET = "set"
    SET_SECRET = "set-secret"
    UNSET_SECRET = "unset-secret"
    CHECK_SECRETS = "check-secrets"


class SpecialCommand(StrEnum):
    """Argparse built-in commands handled outside handlers_factory.

    These are not dispatched to command modules; they are processed directly in main().
    """

    HELP = "help"
    VERSION = "version"


_TOPICS_FILENAME = "topics.json"
_PENDING_FILENAME = "pending_suggestions.json"

PendingEntry = TypeVar("PendingEntry", PendingTopicSuggestion, PendingPurposeSuggestion)
IdSelector = Literal["all"] | list[int]


def _load_topics() -> dict:
    from social_research_probe.config import load_active_config

    data_dir = load_active_config().data_dir
    path = data_dir / _TOPICS_FILENAME
    data = read_json(path, default_factory=default_topics)
    data = migrate_to_current(path, data, kind="topics")
    validate(data, TOPICS_SCHEMA)
    return data


def _save_topics(data: dict) -> None:
    from social_research_probe.config import load_active_config

    data_dir = load_active_config().data_dir
    topics = data["topics"]
    if len(topics) != len(set(topics)):
        raise DuplicateError("internal error: attempted to save duplicate topics")
    data["topics"] = sorted(topics)
    validate(data, TOPICS_SCHEMA)
    atomic_write_json(data_dir / _TOPICS_FILENAME, data)


def show_topics() -> list[str]:
    """Return the current list of topics from state."""
    return list(_load_topics()["topics"])


def _check_topic_duplicates(
    values: list[str], existing: list[str], force: bool
) -> tuple[list[str], list[tuple[str, list[str]]]]:
    """Classify each value against existing topics; return (to_add, conflicts)."""
    to_add: list[str] = []
    conflicts: list[tuple[str, list[str]]] = []
    for value in values:
        result = classify(value, existing + to_add)
        if result.status is DuplicateStatus.NEW or force:
            to_add.append(value)
        else:
            conflicts.append((value, result.matches))
    return to_add, conflicts


def _merge_new_topics(data: dict, existing: list[str], to_add: list[str]) -> None:
    """Deduplicate to_add against existing and append to data, then save."""
    seen = set(existing)
    deduped: list[str] = []
    for v in to_add:
        if v not in seen:
            deduped.append(v)
            seen.add(v)
    data["topics"] = existing + deduped
    _save_topics(data)


def add_topics(values: list[str], *, force: bool) -> None:
    """Add one or more topics, checking for duplicates unless force is True."""
    data = _load_topics()
    existing = list(data["topics"])
    to_add, conflicts = _check_topic_duplicates(values, existing, force)
    if conflicts and not force:
        descriptions = "; ".join(f"{v!r} ~ {m}" for v, m in conflicts)
        raise DuplicateError(
            f"duplicate/near-duplicate topics: {descriptions} (use --force to override)"
        )
    _merge_new_topics(data, existing, to_add)


def remove_topics(values: list[str]) -> None:
    """Remove topics by exact name. Raises ValidationError if any not found."""
    data = _load_topics()
    existing = list(data["topics"])
    not_found = [v for v in values if v not in existing]
    if not_found:
        raise ValidationError(f"topics not found: {not_found}")
    data["topics"] = [t for t in existing if t not in set(values)]
    _save_topics(data)


def rename_topic(old: str, new: str) -> None:
    """Rename a topic. Raises ValidationError if old not found or new already exists."""
    data = _load_topics()
    existing = list(data["topics"])
    if old not in existing:
        raise ValidationError(f"topic not found: {old!r}")
    if new in existing:
        raise ValidationError(f"topic already exists: {new!r}")
    data["topics"] = [new if t == old else t for t in existing]
    _save_topics(data)


def show_purposes() -> dict:
    """Return the current purposes registry as a plain dict."""
    from social_research_probe.utils.purposes import registry

    data = registry.load()
    out = {}
    for name, entry in data["purposes"].items():
        out[name] = {
            "method": entry["method"],
            "evidence_priorities": list(entry.get("evidence_priorities", [])),
            "scoring_overrides": dict(entry.get("scoring_overrides", {})),
        }
    return out


def _validate_purpose_addition(name: str, existing_names: list[str], force: bool) -> None:
    """Raise DuplicateError if name conflicts with existing purposes."""
    result = classify(name, existing_names)
    if result.status in (DuplicateStatus.DUPLICATE, DuplicateStatus.NEAR_DUPLICATE) and not force:
        raise DuplicateError(
            f"purpose {name!r} {result.status.value} with {result.matches} (use --force to override)"
        )
    if name in existing_names and force:
        raise DuplicateError(
            f"purpose {name!r} already exists; use rename to update an existing purpose"
        )


def add_purpose(*, name: str, method: str, force: bool) -> None:
    """Add a new purpose entry, checking for duplicates unless force is True."""
    from social_research_probe.utils.purposes import registry

    if not method.strip():
        raise ValidationError("purpose method cannot be empty")

    data = registry.load()
    existing_names = list(data["purposes"].keys())
    _validate_purpose_addition(name, existing_names, force)

    data["purposes"][name] = {
        "method": method,
        "evidence_priorities": [],
        "scoring_overrides": {},
    }
    registry.save(data)


def remove_purposes(names: list[str]) -> None:
    """Remove purposes by exact name. Raises ValidationError if any not found."""
    from social_research_probe.utils.purposes import registry

    data = registry.load()
    not_found = [n for n in names if n not in data["purposes"]]
    if not_found:
        raise ValidationError(f"purposes not found: {not_found}")
    for name in names:
        del data["purposes"][name]
    registry.save(data)


def rename_purpose(old: str, new: str) -> None:
    """Rename a purpose. Raises ValidationError if old not found or new already exists."""
    from social_research_probe.utils.purposes import registry

    data = registry.load()
    if old not in data["purposes"]:
        raise ValidationError(f"purpose not found: {old!r}")
    if new in data["purposes"]:
        raise ValidationError(f"purpose already exists: {new!r}")
    data["purposes"][new] = data["purposes"].pop(old)
    registry.save(data)


def load_pending() -> PendingSuggestionsState:
    """Load, migrate, validate, and return pending_suggestions.json."""
    from social_research_probe.config import load_active_config

    data_dir = load_active_config().data_dir
    path = data_dir / _PENDING_FILENAME
    data = read_json(path, default_factory=default_pending_suggestions)
    data = cast(
        PendingSuggestionsState,
        migrate_to_current(path, cast(JSONObject, data), kind="pending_suggestions"),
    )
    validate(data, PENDING_SUGGESTIONS_SCHEMA)
    return data


def save_pending(data: PendingSuggestionsState) -> None:
    """Validate and persist pending_suggestions.json."""
    from social_research_probe.config import load_active_config

    data_dir = load_active_config().data_dir
    validate(data, PENDING_SUGGESTIONS_SCHEMA)
    atomic_write_json(data_dir / _PENDING_FILENAME, data)


def _next_id(entries: list[PendingTopicSuggestion] | list[PendingPurposeSuggestion]) -> int:
    """Return the next monotonically increasing suggestion id."""
    return max((e["id"] for e in entries), default=0) + 1


def select_pending(
    entries: list[PendingEntry], selector: IdSelector
) -> tuple[list[PendingEntry], list[PendingEntry]]:
    """Split entries into the chosen subset and the remaining subset."""
    if selector == "all":
        return entries, []
    ids = set(selector)
    chosen = [e for e in entries if e["id"] in ids]
    remaining = [e for e in entries if e["id"] not in ids]
    return chosen, remaining


def _stage_topic_suggestions(
    pending: PendingSuggestionsState,
    candidates: list[TopicSuggestionCandidate],
    existing_topics: list[str],
) -> None:
    """Add validated topic candidates to pending suggestions."""
    next_id = _next_id(pending["pending_topic_suggestions"])
    for cand in candidates:
        if "value" not in cand:
            raise ValidationError(f"topic candidate missing 'value': {cand}")
        result = classify(cand["value"], existing_topics)
        entry: PendingTopicSuggestion = {
            "id": next_id,
            "value": cand["value"],
            "reason": cand.get("reason", "gap"),
            "duplicate_status": result.status.value,
            "matches": list(result.matches),
        }
        pending["pending_topic_suggestions"].append(entry)
        next_id += 1


def _stage_purpose_suggestions(
    pending: PendingSuggestionsState,
    candidates: list[PurposeSuggestionCandidate],
    existing_purposes: list[str],
) -> None:
    """Add validated purpose candidates to pending suggestions."""
    next_id = _next_id(pending["pending_purpose_suggestions"])
    for cand in candidates:
        if "name" not in cand or "method" not in cand:
            raise ValidationError(f"purpose candidate missing name/method: {cand}")
        result = classify(cand["name"], existing_purposes)
        entry: PendingPurposeSuggestion = {
            "id": next_id,
            "name": cand["name"],
            "method": cand["method"],
            "evidence_priorities": list(cand.get("evidence_priorities", [])),
            "duplicate_status": result.status.value,
            "matches": list(result.matches),
        }
        pending["pending_purpose_suggestions"].append(entry)
        next_id += 1


def stage_suggestions(
    *,
    topic_candidates: list[TopicSuggestionCandidate],
    purpose_candidates: list[PurposeSuggestionCandidate],
) -> PendingSuggestionsState:
    """Stage topic and purpose candidates into pending_suggestions.json."""
    pending = load_pending()
    existing_topics = show_topics()
    existing_purposes = list(show_purposes().keys())

    _stage_topic_suggestions(pending, topic_candidates, existing_topics)
    _stage_purpose_suggestions(pending, purpose_candidates, existing_purposes)

    save_pending(pending)
    return pending


__all__ = [
    "Command",
    "ConfigSubcommand",
    "IdSelector",
    "PendingEntry",
    "ResearchCommand",
    "SpecialCommand",
    "add_purpose",
    "add_topics",
    "load_pending",
    "remove_purposes",
    "remove_topics",
    "rename_purpose",
    "rename_topic",
    "save_pending",
    "select_pending",
    "show_purposes",
    "show_topics",
    "stage_suggestions",
]
