"""Thin wrapper around jsonschema that raises SrpError.ValidationError on failure."""

from __future__ import annotations

from jsonschema import Draft202012Validator

from social_research_probe.utils.core.errors import ValidationError
from social_research_probe.utils.core.types import JSONObject, JSONValue


def validate(data: JSONValue, schema: JSONObject) -> None:
    """Strict validation; raises ValidationError listing all issues.

    This utility is shared across commands, services, and stages, so the rule lives here instead of
    being reimplemented differently at each call site.

    Args:
        data: Input payload at this service, technology, or pipeline boundary.
        schema: JSON schema that the LLM or validator must satisfy.

    Returns:
        None. The result is communicated through state mutation, file/database writes, output, or an
        exception.

    Examples:
        Input:
            validate(
                data={"title": "Example", "url": "https://youtu.be/demo"},
                schema="AI safety",
            )
        Output:
            None
    """
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path))
    if not errors:
        return
    messages = [
        f"{'/'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}" for e in errors
    ]
    raise ValidationError("; ".join(messages))
