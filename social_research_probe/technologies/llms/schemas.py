"""JSON schema constants for structured LLM responses."""

from __future__ import annotations

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
