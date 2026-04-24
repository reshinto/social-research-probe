"""Classify a free-form research query into a (topic, purpose) pair using an LLM.

Loads existing topics and purposes from disk, builds a prompt that prefers
reusing existing names, and tries each configured runner in priority order.
Persists any newly created topic or purpose before returning.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from social_research_probe.commands.purposes import add_purpose
from social_research_probe.commands.topics import add_topics, show_topics
from social_research_probe.utils.core.errors import DuplicateError, ValidationError
from social_research_probe.llm.registry import get_runner
from social_research_probe.llm.schemas import NL_QUERY_CLASSIFICATION_SCHEMA
from social_research_probe.purposes.registry import load
from social_research_probe.utils.core.types import RunnerName
from social_research_probe.utils.progress import log

if TYPE_CHECKING:
    from social_research_probe.config import Config

# Runner candidates in stable priority order; preferred runner is moved to front.
_RUNNER_CANDIDATES: list[RunnerName] = ["claude", "gemini", "codex", "local"]

_MULTI_SPACE = re.compile(r" {2,}")


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

    result = _run_classification(prompt, preferred=cfg.default_structured_runner)

    topic = _normalize(result["topic"])
    purpose_name = _normalize(result["purpose_name"])
    purpose_method = _normalize(result["purpose_method"])

    topic_created = _persist_topic(data_dir, topic)
    purpose_created = _persist_purpose(data_dir, purpose_name, purpose_method)

    return ClassifiedQuery(
        topic=topic,
        purpose_name=purpose_name,
        purpose_method=purpose_method,
        topic_created=topic_created,
        purpose_created=purpose_created,
    )


def _runner_order(preferred: RunnerName) -> list[RunnerName]:
    """Return runner names with the preferred runner first."""
    return [preferred, *[n for n in _RUNNER_CANDIDATES if n != preferred]]


def _run_classification(prompt: str, *, preferred: RunnerName) -> dict:
    """Try each runner in order and return the first valid classification result."""
    for name in _runner_order(preferred):
        runner = get_runner(name)
        if not runner.health_check():
            continue
        try:
            result = runner.run(prompt, schema=NL_QUERY_CLASSIFICATION_SCHEMA)
        except Exception as exc:
            log(f"[srp] nl-query: runner={name} outcome=error err={exc}")
            continue
        if _is_valid_result(result):
            return result
    raise ValidationError(
        "unable to classify query: all LLM runners failed or are unavailable. "
        "Provide explicit topic+purpose instead."
    )


def _is_valid_result(result: dict) -> bool:
    """Return True when result contains all required non-empty string fields."""
    for key in ("topic", "purpose_name", "purpose_method"):
        value = result.get(key)
        if not isinstance(value, str) or not value.strip():
            return False
    return True


def _normalize(value: str) -> str:
    """Strip, lowercase, and collapse internal whitespace."""
    return _MULTI_SPACE.sub(" ", value.strip().lower())


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

Classify the following query into a topic and a purpose:

QUERY: {query}

EXISTING TOPICS (prefer reusing one if semantically close): {topics_str}
EXISTING PURPOSES (prefer reusing one if semantically close): {purposes_str}

Rules:
- topic: 1-4 word lowercase hyphenated label for the subject area (e.g. "ai", "quantitative-finance", "climate-change").
- purpose_name: 1-4 word lowercase hyphenated label for the research goal (e.g. "latest-news", "job-opportunities", "deep-dive").
- purpose_method: short 3-8 word phrase describing HOW to research this (e.g. "latest news and updates", "career paths and hiring trends"). Used to enrich search queries.
- If an existing topic or purpose name is semantically equivalent, use EXACTLY that existing name.

Respond with JSON only, no other text."""
