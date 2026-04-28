"""Command: suggest-topics. Generate and stage new topic suggestions via LLM."""

from __future__ import annotations

import argparse

from social_research_probe.utils.core.exit_codes import ExitCode

_TOPIC_SEED_POOL = [
    "on-device LLMs",
    "robotics foundation models",
    "vector databases",
    "AI-generated video",
    "tool-using agents",
    "model context protocol",
    "open weight models",
    "multimodal agents",
]


def _resolve_runner_or_none() -> str | None:
    """Return the configured runner or ``None`` when LLM is disabled."""
    from social_research_probe.config import load_active_config

    runner = load_active_config().default_structured_runner
    return None if runner == "none" else runner


def _seed_drafts(existing: list[str], count: int) -> list[dict]:
    """Pick deterministic seed topics not already present."""
    candidates = [t for t in _TOPIC_SEED_POOL if t not in set(existing)]
    return [
        {"value": v, "reason": "seed pool (no LLM runner configured)"} for v in candidates[:count]
    ]


def _build_prompt(existing: list[str], count: int) -> str:
    """Format the suggest-topics LLM prompt."""
    from social_research_probe.technologies.llms.prompts import SUGGEST_TOPICS_PROMPT

    return SUGGEST_TOPICS_PROMPT.format(
        existing_topics=", ".join(existing) if existing else "(none yet)",
        count=count,
    )


def _call_llm(prompt: str, runner: str) -> dict:
    """Call the LLM and return the raw result dict."""
    from social_research_probe.technologies.llms.registry import run_with_fallback
    from social_research_probe.technologies.llms.schemas import TOPIC_SUGGESTIONS_SCHEMA

    return run_with_fallback(prompt, TOPIC_SUGGESTIONS_SCHEMA, runner)


def _extract_drafts(result: dict) -> list[dict]:
    """Extract topic suggestion dicts from the LLM result."""
    return [
        {"value": s["value"], "reason": s.get("reason", "")} for s in result.get("suggestions", [])
    ]


def run(args: argparse.Namespace) -> int:
    from social_research_probe.commands import add_pending_suggestions, list_topics
    from social_research_probe.utils.display.cli_output import emit

    runner = _resolve_runner_or_none()
    existing = list_topics()
    if runner is None:
        drafts = _seed_drafts(existing, args.count)
    else:
        prompt = _build_prompt(existing, args.count)
        drafts = _extract_drafts(_call_llm(prompt, runner))
    add_pending_suggestions(topic_candidates=drafts, purpose_candidates=[])
    emit({"staged_topic_suggestions": drafts}, args.output)
    return ExitCode.SUCCESS
