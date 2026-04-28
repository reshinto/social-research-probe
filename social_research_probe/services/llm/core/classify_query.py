"""Classify a free-form research query into a (topic, purpose) pair using an LLM.

Loads existing topics and purposes from disk, builds a prompt that prefers
reusing existing names, and tries each configured runner in priority order.
Persists any newly created topic or purpose before returning.
"""

from __future__ import annotations

from dataclasses import dataclass

from social_research_probe.commands import add_purpose, add_topics, list_topics
from social_research_probe.config import load_active_config
from social_research_probe.utils.llm.prompts import CLASSIFICATION_PROMPT
from social_research_probe.utils.llm.registry import run_with_fallback
from social_research_probe.utils.llm.schemas import NL_QUERY_CLASSIFICATION_SCHEMA
from social_research_probe.utils.caching.pipeline_cache import (
    classification_cache,
    get_json,
    hash_key,
    set_json,
)
from social_research_probe.utils.core.errors import DuplicateError, ValidationError
from social_research_probe.utils.core.strings import normalize_whitespace
from social_research_probe.utils.core.types import RunnerName
from social_research_probe.utils.display.progress import log_with_time
from social_research_probe.utils.purposes.registry import load


@dataclass(frozen=True)
class ClassifiedQuery:
    """Result of classifying a free-form query into a topic and purpose."""

    topic: str
    purpose_name: str
    purpose_method: str
    topic_created: bool
    purpose_created: bool


def _validate_llm_config() -> str:
    """Validate LLM config is enabled and return the preferred runner."""
    cfg = load_active_config()
    if not cfg.service_enabled("llm"):
        raise ValidationError(
            "cannot classify query: services.llm is false. "
            "Provide explicit topic+purpose or enable the LLM service."
        )
    if cfg.default_structured_runner == "none":
        raise ValidationError(
            "cannot classify query: llm.runner is disabled. "
            "Provide explicit topic+purpose or set llm.runner in srp config."
        )
    return cfg.default_structured_runner


def _persist_classification_result(
    topic: str, purpose_name: str, purpose_method: str
) -> tuple[bool, bool]:
    """Persist topic and purpose; return (topic_created, purpose_created)."""
    topic_created = _persist_topic(topic)
    purpose_created = _persist_purpose(purpose_name, purpose_method)
    return topic_created, purpose_created


def classify_query(query: str) -> ClassifiedQuery:
    """Classify a free-form query into (topic, purpose) and persist new entries."""
    preferred_runner = _validate_llm_config()

    existing_topics = list_topics()
    existing_purposes = list(load()["purposes"].keys())
    prompt = _build_classification_prompt(query, existing_topics, existing_purposes)

    result = _run_classification(prompt, preferred=preferred_runner)

    topic = normalize_whitespace(result["topic"])
    purpose_name = normalize_whitespace(result["purpose_name"])
    purpose_method = normalize_whitespace(result["purpose_method"])

    topic_created, purpose_created = _persist_classification_result(
        topic, purpose_name, purpose_method
    )

    return ClassifiedQuery(
        topic=topic,
        purpose_name=purpose_name,
        purpose_method=purpose_method,
        topic_created=topic_created,
        purpose_created=purpose_created,
    )


@log_with_time("[srp] _run_classification: classifying query")
def _run_classification(prompt: str, *, preferred: RunnerName) -> dict:
    """Try each runner in order and return the first valid classification result."""
    cache_key = hash_key(prompt)
    cached = get_json(classification_cache(), cache_key)
    if cached is not None:
        return cached["result"]

    result = run_with_fallback(prompt, NL_QUERY_CLASSIFICATION_SCHEMA, preferred)

    if _is_valid_result(result):
        cache_entry = {"prompt": prompt, "result": result}
        set_json(classification_cache(), cache_key, cache_entry)
        return result

    raise ValidationError(
        "classification result is invalid: missing or empty required fields. "
        "Provide explicit topic+purpose instead."
    )


def _is_valid_result(result: dict) -> bool:
    """Return True when result contains all required non-empty string fields."""
    for key in ("topic", "purpose_name", "purpose_method"):
        value = result.get(key)
        if not isinstance(value, str) or not value.strip():
            return False
    return True


def _persist_topic(topic: str) -> bool:
    """Add the topic; return True if created, False if it already existed."""
    try:
        add_topics([topic], force=False)
        return True
    except DuplicateError:
        return False


def _persist_purpose(name: str, method: str) -> bool:
    """Add the purpose; return True if created, False if it already existed."""
    try:
        add_purpose(name=name, method=method, force=False)
        return True
    except DuplicateError:
        return False


def _build_classification_prompt(
    query: str,
    existing_topics: list[str],
    existing_purposes: list[str],
) -> str:
    """Build the LLM prompt that instructs classification with existing-name preference."""
    topics_str = ", ".join(existing_topics) if existing_topics else "(none yet)"
    purposes_str = ", ".join(existing_purposes) if existing_purposes else "(none yet)"

    return CLASSIFICATION_PROMPT.format(
        query=query,
        existing_topics=topics_str,
        existing_purposes=purposes_str,
    )
