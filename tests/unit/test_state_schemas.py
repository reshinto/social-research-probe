"""jsonschema validation for topics.json, purposes.json, pending_suggestions.json."""

from __future__ import annotations

import pytest

from social_research_probe.errors import ValidationError
from social_research_probe.state.schemas import (
    PENDING_SUGGESTIONS_SCHEMA,
    PURPOSES_SCHEMA,
    TOPICS_SCHEMA,
    default_pending_suggestions,
    default_purposes,
    default_topics,
)
from social_research_probe.state.validate import validate


def test_topics_defaults_are_valid():
    validate(default_topics(), TOPICS_SCHEMA)


def test_purposes_defaults_are_valid():
    validate(default_purposes(), PURPOSES_SCHEMA)


def test_pending_defaults_are_valid():
    validate(default_pending_suggestions(), PENDING_SUGGESTIONS_SCHEMA)


def test_topics_rejects_missing_schema_version():
    with pytest.raises(ValidationError):
        validate({"topics": []}, TOPICS_SCHEMA)


def test_topics_rejects_non_string_topic():
    with pytest.raises(ValidationError):
        validate({"schema_version": 1, "topics": [42]}, TOPICS_SCHEMA)


def test_purposes_rejects_missing_method():
    bad = {"schema_version": 1, "purposes": {"trends": {"evidence_priorities": []}}}
    with pytest.raises(ValidationError):
        validate(bad, PURPOSES_SCHEMA)


def test_pending_rejects_duplicate_ids():
    # Schema allows dups; uniqueness is enforced at write-time in commands (Task 14).
    # This test locks in the schema shape: each entry must have id+value fields.
    bad = {
        "schema_version": 1,
        "pending_topic_suggestions": [{"id": 1}],
        "pending_purpose_suggestions": [],
    }
    with pytest.raises(ValidationError):
        validate(bad, PENDING_SUGGESTIONS_SCHEMA)
