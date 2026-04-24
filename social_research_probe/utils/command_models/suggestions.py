"""Rule-based suggestions + staging. Host-LLM enhancement lands in P4."""

from __future__ import annotations

from pathlib import Path
from typing import Literal, TypeVar, cast

from social_research_probe.utils.command_models.purposes import add_purpose
from social_research_probe.utils.command_models.topics import add_topics
from social_research_probe.utils.core.dedupe import DuplicateStatus, classify
from social_research_probe.utils.core.errors import DuplicateError, ValidationError
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
    default_pending_suggestions,
)
from social_research_probe.utils.state.store import atomic_write_json, read_json
from social_research_probe.utils.state.validate import validate

_FILENAME = "pending_suggestions.json"

_TOPIC_SEED_POOL = [
    "on-device LLMs",
    "robotics foundation models",
    "vector databases",
    "AI-generated video",
    "tool-using agents",
    "model context protocol",
    "open weight models",
    "multimodal agents",
]

_PURPOSE_SEED_POOL = [
    ("saturation-analysis", "Detect when a topic has peaked; measure repetition across channels."),
    ("audience-fit", "Match content style to viewer demographics; gauge retention signals."),
    ("arbitrage", "Find pricing/attention spreads between platforms or niches."),
    ("job-opportunities", "Identify hiring signals and skill demand from creator content."),
]

PendingEntry = TypeVar("PendingEntry", PendingTopicSuggestion, PendingPurposeSuggestion)


def _load_pending(data_dir: Path) -> PendingSuggestionsState:
    """Load, migrate, validate, and return pending_suggestions.json."""
    path = data_dir / _FILENAME
    data = read_json(path, default_factory=default_pending_suggestions)
    data = cast(
        PendingSuggestionsState,
        migrate_to_current(path, cast(JSONObject, data), kind="pending_suggestions"),
    )
    validate(data, PENDING_SUGGESTIONS_SCHEMA)
    return data


def _save_pending(data_dir: Path, data: PendingSuggestionsState) -> None:
    """Validate and persist pending_suggestions.json."""
    validate(data, PENDING_SUGGESTIONS_SCHEMA)
    atomic_write_json(data_dir / _FILENAME, data)


def _next_id(entries: list[PendingTopicSuggestion] | list[PendingPurposeSuggestion]) -> int:
    """Return the next monotonically increasing suggestion id."""
    return max((e["id"] for e in entries), default=0) + 1


def suggest_topics(data_dir: Path, count: int = 5) -> list[TopicSuggestionCandidate]:
    """Generate new topic suggestions from the fixed seed pool."""
    from social_research_probe.utils.command_models.topics import show_topics

    existing = show_topics(data_dir)
    drafts: list[TopicSuggestionCandidate] = []
    for candidate in _TOPIC_SEED_POOL:
        if len(drafts) >= count:
            break
        if classify(candidate, existing).status is DuplicateStatus.NEW:
            drafts.append({"value": candidate, "reason": "gap"})
    return drafts


def suggest_purposes(data_dir: Path, count: int = 5) -> list[PurposeSuggestionCandidate]:
    """Generate new purpose suggestions from the fixed seed pool."""
    from social_research_probe.utils.command_models.purposes import show_purposes

    existing = list(show_purposes(data_dir).keys())
    drafts: list[PurposeSuggestionCandidate] = []
    for name, method in _PURPOSE_SEED_POOL:
        if len(drafts) >= count:
            break
        if classify(name, existing).status is DuplicateStatus.NEW:
            drafts.append({"name": name, "method": method, "evidence_priorities": []})
    return drafts


def stage_suggestions(
    data_dir: Path,
    *,
    topic_candidates: list[TopicSuggestionCandidate],
    purpose_candidates: list[PurposeSuggestionCandidate],
) -> PendingSuggestionsState:
    """Stage topic and purpose candidates into pending_suggestions.json."""
    from social_research_probe.utils.command_models.purposes import show_purposes
    from social_research_probe.utils.command_models.topics import show_topics

    pending = _load_pending(data_dir)
    existing_topics = show_topics(data_dir)
    existing_purposes = list(show_purposes(data_dir).keys())

    next_topic_id = _next_id(pending["pending_topic_suggestions"])
    for cand in topic_candidates:
        if "value" not in cand:
            raise ValidationError(f"topic candidate missing 'value': {cand}")
        result = classify(cand["value"], existing_topics)
        entry: PendingTopicSuggestion = {
            "id": next_topic_id,
            "value": cand["value"],
            "reason": cand.get("reason", "gap"),
            "duplicate_status": result.status.value,
            "matches": list(result.matches),
        }
        pending["pending_topic_suggestions"].append(entry)
        next_topic_id += 1

    next_purpose_id = _next_id(pending["pending_purpose_suggestions"])
    for cand in purpose_candidates:
        if "name" not in cand or "method" not in cand:
            raise ValidationError(f"purpose candidate missing name/method: {cand}")
        result = classify(cand["name"], existing_purposes)
        entry: PendingPurposeSuggestion = {
            "id": next_purpose_id,
            "name": cand["name"],
            "method": cand["method"],
            "evidence_priorities": list(cand.get("evidence_priorities", [])),
            "duplicate_status": result.status.value,
            "matches": list(result.matches),
        }
        pending["pending_purpose_suggestions"].append(entry)
        next_purpose_id += 1

    _save_pending(data_dir, pending)
    return pending


def show_pending(data_dir: Path) -> PendingSuggestionsState:
    """Return the pending suggestions state file."""
    return _load_pending(data_dir)


IdSelector = Literal["all"] | list[int]


def _select(
    entries: list[PendingEntry], selector: IdSelector
) -> tuple[list[PendingEntry], list[PendingEntry]]:
    """Split entries into the chosen subset and the remaining subset."""
    if selector == "all":
        return entries, []
    ids = set(selector)
    chosen = [e for e in entries if e["id"] in ids]
    remaining = [e for e in entries if e["id"] not in ids]
    return chosen, remaining


def apply_pending(data_dir: Path, *, topic_ids: IdSelector, purpose_ids: IdSelector) -> None:
    pending = _load_pending(data_dir)

    topic_chosen, topic_rest = _select(pending["pending_topic_suggestions"], topic_ids)
    purpose_chosen, purpose_rest = _select(pending["pending_purpose_suggestions"], purpose_ids)

    for entry in topic_chosen:
        try:
            add_topics(data_dir, [entry["value"]], force=False)
        except DuplicateError:
            topic_rest.append(entry)

    for entry in purpose_chosen:
        try:
            add_purpose(data_dir, name=entry["name"], method=entry["method"], force=False)
        except DuplicateError:
            purpose_rest.append(entry)

    pending["pending_topic_suggestions"] = topic_rest
    pending["pending_purpose_suggestions"] = purpose_rest
    _save_pending(data_dir, pending)


def discard_pending(data_dir: Path, *, topic_ids: IdSelector, purpose_ids: IdSelector) -> None:
    pending = _load_pending(data_dir)
    _, topic_rest = _select(pending["pending_topic_suggestions"], topic_ids)
    _, purpose_rest = _select(pending["pending_purpose_suggestions"], purpose_ids)
    pending["pending_topic_suggestions"] = topic_rest
    pending["pending_purpose_suggestions"] = purpose_rest
    _save_pending(data_dir, pending)
