"""jsonschema definitions + default factories for every state file."""
from __future__ import annotations

from typing import Any

SCHEMA_VERSION = 1

TOPICS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["schema_version", "topics"],
    "additionalProperties": False,
    "properties": {
        "schema_version": {"type": "integer", "minimum": 0},
        "topics": {"type": "array", "items": {"type": "string", "minLength": 1}},
    },
}

PURPOSE_ENTRY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["method", "evidence_priorities"],
    "additionalProperties": False,
    "properties": {
        "method": {"type": "string", "minLength": 1},
        "evidence_priorities": {"type": "array", "items": {"type": "string"}},
        "scoring_overrides": {"type": "object"},
    },
}

PURPOSES_SCHEMA: dict[str, Any] = {
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

PENDING_TOPIC_ENTRY_SCHEMA: dict[str, Any] = {
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

PENDING_PURPOSE_ENTRY_SCHEMA: dict[str, Any] = {
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

PENDING_SUGGESTIONS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["schema_version", "pending_topic_suggestions", "pending_purpose_suggestions"],
    "additionalProperties": False,
    "properties": {
        "schema_version": {"type": "integer", "minimum": 0},
        "pending_topic_suggestions": {"type": "array", "items": PENDING_TOPIC_ENTRY_SCHEMA},
        "pending_purpose_suggestions": {"type": "array", "items": PENDING_PURPOSE_ENTRY_SCHEMA},
    },
}


def default_topics() -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "topics": []}


def default_purposes() -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "purposes": {}}


def default_pending_suggestions() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "pending_topic_suggestions": [],
        "pending_purpose_suggestions": [],
    }
