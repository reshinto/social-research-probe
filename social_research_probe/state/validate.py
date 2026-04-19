"""Thin wrapper around jsonschema that raises SrpError.ValidationError on failure."""

from __future__ import annotations

from jsonschema import Draft202012Validator

from social_research_probe.errors import ValidationError
from social_research_probe.types import JSONObject, JSONValue


def validate(data: JSONValue, schema: JSONObject) -> None:
    """Strict validation; raises ValidationError listing all issues."""
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path))
    if not errors:
        return
    messages = [
        f"{'/'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}" for e in errors
    ]
    raise ValidationError("; ".join(messages))
