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

CLAIM_EXTRACTION_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "claim_text": {"type": "string", "minLength": 1},
                    "claim_type": {
                        "type": "string",
                        "enum": [
                            "fact_claim",
                            "opinion",
                            "prediction",
                            "recommendation",
                            "experience",
                            "question",
                            "objection",
                            "pain_point",
                            "market_signal",
                        ],
                    },
                    "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                    "entities": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "needs_corroboration": {"type": "boolean"},
                    "uncertainty": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                    },
                },
                "required": ["claim_text", "claim_type", "confidence"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["claims"],
    "additionalProperties": False,
}
