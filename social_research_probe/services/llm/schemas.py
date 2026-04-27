"""JSON schema constants for structured LLM responses."""

from __future__ import annotations

TOPIC_SUGGESTIONS_SCHEMA = {
    "type": "object",
    "properties": {
        "suggestions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "value": {"type": "string", "minLength": 1},
                    "reason": {"type": "string"},
                },
                "required": ["value"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["suggestions"],
    "additionalProperties": False,
}

PURPOSE_SUGGESTIONS_SCHEMA = {
    "type": "object",
    "properties": {
        "suggestions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "minLength": 1},
                    "method": {"type": "string", "minLength": 1},
                },
                "required": ["name", "method"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["suggestions"],
    "additionalProperties": False,
}

NL_QUERY_CLASSIFICATION_SCHEMA = {
    "type": "object",
    "properties": {
        "topic": {"type": "string", "minLength": 1, "maxLength": 60},
        "purpose_name": {"type": "string", "minLength": 1, "maxLength": 60},
        "purpose_method": {"type": "string", "minLength": 1, "maxLength": 200},
    },
    "required": ["topic", "purpose_name", "purpose_method"],
    "additionalProperties": False,
}
