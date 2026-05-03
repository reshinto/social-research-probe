"""jsonschema definitions + default factories for every state file."""

from __future__ import annotations

from social_research_probe.utils.core.types import (
    JSONObject,
    PendingSuggestionsState,
    PurposesState,
    TopicsState,
)

SCHEMA_VERSION = 1

TOPICS_SCHEMA: JSONObject = {
    "type": "object",
    "required": ["schema_version", "topics"],
    "additionalProperties": False,
    "properties": {
        "schema_version": {"type": "integer", "minimum": 0},
        "topics": {"type": "array", "items": {"type": "string", "minLength": 1}},
    },
}

PURPOSE_ENTRY_SCHEMA: JSONObject = {
    "type": "object",
    "required": ["method", "evidence_priorities"],
    "additionalProperties": False,
    "properties": {
        "method": {"type": "string", "minLength": 1},
        "evidence_priorities": {"type": "array", "items": {"type": "string"}},
        "scoring_overrides": {"type": "object"},
    },
}

PURPOSES_SCHEMA: JSONObject = {
    "type": "object",
    "required": ["schema_version", "purposes"],
    "additionalProperties": False,
    "properties": {
        "schema_version": {"type": "integer", "minimum": 0},
        "purposes": {
            "type": "object",
            "additionalProperties": PURPOSE_ENTRY_SCHEMA,
        },
    },
}

PENDING_TOPIC_ENTRY_SCHEMA: JSONObject = {
    "type": "object",
    "required": ["id", "value", "reason", "duplicate_status", "matches"],
    "additionalProperties": False,
    "properties": {
        "id": {"type": "integer", "minimum": 1},
        "value": {"type": "string", "minLength": 1},
        "reason": {"type": "string"},
        "duplicate_status": {"enum": ["new", "near-duplicate", "duplicate"]},
        "matches": {"type": "array", "items": {"type": "string"}},
    },
}

PENDING_PURPOSE_ENTRY_SCHEMA: JSONObject = {
    "type": "object",
    "required": ["id", "name", "method", "evidence_priorities", "duplicate_status", "matches"],
    "additionalProperties": False,
    "properties": {
        "id": {"type": "integer", "minimum": 1},
        "name": {"type": "string", "minLength": 1},
        "method": {"type": "string", "minLength": 1},
        "evidence_priorities": {"type": "array", "items": {"type": "string"}},
        "duplicate_status": {"enum": ["new", "near-duplicate", "duplicate"]},
        "matches": {"type": "array", "items": {"type": "string"}},
    },
}

PENDING_SUGGESTIONS_SCHEMA: JSONObject = {
    "type": "object",
    "required": ["schema_version", "pending_topic_suggestions", "pending_purpose_suggestions"],
    "additionalProperties": False,
    "properties": {
        "schema_version": {"type": "integer", "minimum": 0},
        "pending_topic_suggestions": {"type": "array", "items": PENDING_TOPIC_ENTRY_SCHEMA},
        "pending_purpose_suggestions": {"type": "array", "items": PENDING_PURPOSE_ENTRY_SCHEMA},
    },
}


def default_topics() -> TopicsState:
    """Document the default topics rule at the boundary where callers use it.

    This utility is shared across commands, services, and stages, so the rule lives here instead of
    being reimplemented differently at each call site.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            default_topics()
        Output:
            "AI safety"
    """
    return {"schema_version": SCHEMA_VERSION, "topics": []}


def default_purposes() -> PurposesState:
    """Document the default purposes rule at the boundary where callers use it.

    This utility is shared across commands, services, and stages, so the rule lives here instead of
    being reimplemented differently at each call site.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            default_purposes()
        Output:
            "AI safety"
    """
    return {"schema_version": SCHEMA_VERSION, "purposes": {}}


def default_pending_suggestions() -> PendingSuggestionsState:
    """Document the default pending suggestions rule at the boundary where callers use it.

    This utility is shared across commands, services, and stages, so the rule lives here instead of
    being reimplemented differently at each call site.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            default_pending_suggestions()
        Output:
            "AI safety"
    """
    return {
        "schema_version": SCHEMA_VERSION,
        "pending_topic_suggestions": [],
        "pending_purpose_suggestions": [],
    }
