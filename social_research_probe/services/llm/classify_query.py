"""Classify a free-form research query into a (topic, purpose) pair using an LLM.

Loads existing topics and purposes from disk, builds a prompt that prefers
reusing existing names, and tries each configured runner in priority order.
Persists any newly created topic or purpose before returning.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from social_research_probe.technologies.llms.registry import run_with_fallback
from social_research_probe.technologies.llms.schemas import (
    NL_QUERY_CLASSIFICATION_SCHEMA,
)
from social_research_probe.utils.caching.pipeline_cache import (
    classification_cache,
    get_json,
    hash_key,
    set_json,
)
from social_research_probe.utils.command_models.purposes import add_purpose
from social_research_probe.utils.command_models.topics import add_topics, show_topics
from social_research_probe.utils.core.errors import DuplicateError, ValidationError
from social_research_probe.utils.core.strings import normalize_whitespace
from social_research_probe.utils.core.types import RunnerName
from social_research_probe.utils.display.progress import log_with_time
from social_research_probe.utils.purposes.registry import load

if TYPE_CHECKING:
    from social_research_probe.config import Config

@dataclass(frozen=True)
class ClassifiedQuery:
    """Result of classifying a free-form query into a topic and purpose."""

    topic: str
    purpose_name: str
    purpose_method: str
    topic_created: bool
    purpose_created: bool


def classify_query(query: str, *, data_dir: Path, cfg: Config) -> ClassifiedQuery:
    """Classify a free-form query into (topic, purpose) and persist new entries."""
    if hasattr(cfg, "service_enabled") and not cfg.service_enabled("llm"):
        raise ValidationError(
            "cannot classify query: services.llm is false. "
            "Provide explicit topic+purpose or enable the LLM service."
        )
    if cfg.default_structured_runner == "none":
        raise ValidationError(
            "cannot classify query: llm.runner is disabled. "
            "Provide explicit topic+purpose or set llm.runner in srp config."
        )

    existing_topics = show_topics(data_dir)
    existing_purposes = list(load(data_dir)["purposes"].keys())
    prompt = _build_classification_prompt(query, existing_topics, existing_purposes)

    result = run_classification(prompt, preferred=cfg.default_structured_runner)

    topic = normalize_whitespace(result["topic"])
    purpose_name = normalize_whitespace(result["purpose_name"])
    purpose_method = normalize_whitespace(result["purpose_method"])

    topic_created = _persist_topic(data_dir, topic)
    purpose_created = _persist_purpose(data_dir, purpose_name, purpose_method)

    return ClassifiedQuery(
        topic=topic,
        purpose_name=purpose_name,
        purpose_method=purpose_method,
        topic_created=topic_created,
        purpose_created=purpose_created,
    )


@log_with_time("[srp] run_classification: classifying query")
def run_classification(prompt: str, *, preferred: RunnerName) -> dict:
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


def _persist_topic(data_dir: Path, topic: str) -> bool:
    """Add the topic; return True if created, False if it already existed."""
    try:
        add_topics(data_dir, [topic], force=False)
        return True
    except DuplicateError:
        return False


def _persist_purpose(data_dir: Path, name: str, method: str) -> bool:
    """Add the purpose; return True if created, False if it already existed."""
    try:
        add_purpose(data_dir, name=name, method=method, force=False)
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

    return f"""You are classifying a research query for a social media research tool.

Classify the following query into a topic and a purpose.

QUERY: {query}

EXISTING TOPICS (prefer reuse if meaningfully similar): {topics_str}
EXISTING PURPOSES (prefer reuse if meaningfully similar): {purposes_str}

Rules:
- topic: 1-4 word lowercase hyphenated label for the subject area (e.g. "ai", "quantitative-finance", "climate-change").
- purpose_name: 1-4 word lowercase hyphenated label for the research goal (e.g. "latest-news", "job-opportunities", "deep-dive").
- purpose_method: 3-8 word phrase describing how to research this. Used to expand search queries.

Reuse rules:
- If an existing topic or purpose_name is even moderately similar in meaning, reuse it EXACTLY.
- Only create a new label if no existing option is a reasonable fit.
- Prefer broader existing categories over creating new narrow ones.

Output format (JSON only):
{{
  "topic": "...",
  "purpose_name": "...",
  "purpose_method": "..."
}}"""
