"""Classify a free-form research query into a (topic, purpose) pair using an LLM.

Loads existing topics and purposes from disk, builds a prompt that prefers
reusing existing names, and tries each configured runner in priority order.
Persists any newly created topic or purpose before returning.
"""

from __future__ import annotations

from dataclasses import dataclass

from social_research_probe.commands import add_purpose, add_topics, list_topics
from social_research_probe.config import load_active_config
from social_research_probe.utils.core.errors import DuplicateError, ValidationError
from social_research_probe.utils.core.strings import normalize_whitespace
from social_research_probe.utils.core.types import RunnerName
from social_research_probe.utils.display.progress import log_with_time
from social_research_probe.utils.llm.prompts import CLASSIFICATION_PROMPT
from social_research_probe.utils.llm.registry import run_with_fallback
from social_research_probe.utils.llm.schemas import NL_QUERY_CLASSIFICATION_SCHEMA
from social_research_probe.utils.purposes.registry import load


@dataclass(frozen=True)
class ClassifiedQuery:
    """Result of classifying a free-form query into a topic and purpose.

    Examples:
        Input:
            ClassifiedQuery
        Output:
            ClassifiedQuery
    """

    topic: str
    purpose_name: str
    purpose_method: str
    topic_created: bool
    purpose_created: bool


def _validate_llm_config() -> str:
    """Validate LLM config is enabled and return the preferred runner.

    Services translate platform data into adapter calls and normalize the result so stages can
    handle success, skip, and failure consistently.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _validate_llm_config()
        Output:
            "AI safety"
    """
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
    """Persist topic and purpose; return (topic_created, purpose_created).

    Services translate platform data into adapter calls and normalize the result so stages can
    handle success, skip, and failure consistently.

    Args:
        topic: Research topic text or existing topic list used for classification and suggestions.
        purpose_name: Purpose name or purpose definitions that shape the research goal.
        purpose_method: Purpose method text that explains how the research should be evaluated.

    Returns:
        None. The result is communicated through state mutation, file/database writes, output, or an
        exception.

    Examples:
        Input:
            _persist_classification_result(
                topic="AI safety",
                purpose_name="Opportunity Map",
                purpose_method="Find unmet needs",
            )
        Output:
            None
    """
    topic_created = _persist_topic(topic)
    purpose_created = _persist_purpose(purpose_name, purpose_method)
    return topic_created, purpose_created


def classify_query(query: str) -> ClassifiedQuery:
    """Document the classify query rule at the boundary where callers use it.

    Services translate platform data into adapter calls and normalize the result so stages can
    handle success, skip, and failure consistently.

    Args:
        query: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
               to a provider.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            classify_query(
                query="AI safety benchmarks",
            )
        Output:
            "AI safety"
    """
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
    """Try each runner in order and return the first valid classification result.

    Services translate platform data into adapter calls and normalize the result so stages can
    handle success, skip, and failure consistently.

    Args:
        prompt: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
                to a provider.
        preferred: Provider or runner selected for this operation.

    Returns:
        Dictionary with stable keys consumed by downstream project code.

    Examples:
        Input:
            _run_classification(
                prompt="Summarize this source.",
                preferred="codex",
            )
        Output:
            {"enabled": True}
    """
    result = run_with_fallback(prompt, NL_QUERY_CLASSIFICATION_SCHEMA, preferred)

    if _is_valid_result(result):
        return result

    raise ValidationError(
        "classification result is invalid: missing or empty required fields. "
        "Provide explicit topic+purpose instead."
    )


def _is_valid_result(result: dict) -> bool:
    """Return True when result contains all required non-empty string fields.

    Args:
        result: Service or technology result being inspected for payload and diagnostics.

    Returns:
        True when the condition is satisfied; otherwise False.

    Examples:
        Input:
            _is_valid_result(
                result=ServiceResult(service_name="comments", input_key="demo", tech_results=[]),
            )
        Output:
            True
    """
    for key in ("topic", "purpose_name", "purpose_method"):
        value = result.get(key)
        if not isinstance(value, str) or not value.strip():
            return False
    return True


def _persist_topic(topic: str) -> bool:
    """Add the topic; return True if created, False if it already existed.

    Args:
        topic: Research topic text or existing topic list used for classification and suggestions.

    Returns:
        None. The result is communicated through state mutation, file/database writes, output, or an
        exception.

    Examples:
        Input:
            _persist_topic(
                topic="AI safety",
            )
        Output:
            None
    """
    try:
        add_topics([topic], force=False)
        return True
    except DuplicateError:
        return False


def _persist_purpose(name: str, method: str) -> bool:
    """Add the purpose; return True if created, False if it already existed.

    Services turn platform items into adapter requests and normalize results so stages handle
    success, skip, and failure the same way.

    Args:
        name: Registry, config, or CLI name used to select the matching project value.
        method: Purpose method text that explains how the research should be evaluated.

    Returns:
        None. The result is communicated through state mutation, file/database writes, output, or an
        exception.

    Examples:
        Input:
            _persist_purpose(
                name="AI safety",
                method="Find unmet needs",
            )
        Output:
            None
    """
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
    """Build the LLM prompt that instructs classification with existing-name preference.

    Services translate platform data into adapter calls and normalize the result so stages can
    handle success, skip, and failure consistently.

    Args:
        query: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
               to a provider.
        existing_topics: Research topic text or existing topic list used for classification and
                         suggestions.
        existing_purposes: Purpose name or purpose definitions that shape the research goal.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _build_classification_prompt(
                query="AI safety benchmarks",
                existing_topics=["AI safety"],
                existing_purposes=[{"name": "Opportunity Map"}],
            )
        Output:
            "AI safety"
    """
    topics_str = ", ".join(existing_topics) if existing_topics else "(none yet)"
    purposes_str = ", ".join(existing_purposes) if existing_purposes else "(none yet)"

    return CLASSIFICATION_PROMPT.format(
        query=query,
        existing_topics=topics_str,
        existing_purposes=purposes_str,
    )
