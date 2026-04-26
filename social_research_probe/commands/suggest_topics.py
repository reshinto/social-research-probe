"""Command: suggest-topics. Generate and stage new topic suggestions via LLM."""

from __future__ import annotations

import argparse

from social_research_probe.utils.core.exit_codes import ExitCode


def _validate_llm_runner() -> str:
    """Return the configured runner or raise if disabled."""
    from social_research_probe.config import load_active_config
    from social_research_probe.utils.core.errors import ValidationError

    cfg = load_active_config()
    if cfg.default_structured_runner == "none":
        raise ValidationError("suggest-topics requires an LLM runner (set llm.runner in config)")
    return cfg.default_structured_runner


def _build_prompt(existing: list[str], count: int) -> str:
    """Format the suggest-topics LLM prompt."""
    from social_research_probe.services.llm.prompts import SUGGEST_TOPICS_PROMPT

    return SUGGEST_TOPICS_PROMPT.format(
        existing_topics=", ".join(existing) if existing else "(none yet)",
        count=count,
    )


def _call_llm(prompt: str, runner: str) -> dict:
    """Call the LLM and return the raw result dict."""
    from social_research_probe.services.llm.registry import run_with_fallback
    from social_research_probe.services.llm.schemas import TOPIC_SUGGESTIONS_SCHEMA

    return run_with_fallback(prompt, TOPIC_SUGGESTIONS_SCHEMA, runner)


def _extract_drafts(result: dict) -> list[dict]:
    """Extract topic suggestion dicts from the LLM result."""
    return [
        {"value": s["value"], "reason": s.get("reason", "")} for s in result.get("suggestions", [])
    ]


def run(args: argparse.Namespace) -> int:
    from social_research_probe.commands import show_topics, stage_suggestions
    from social_research_probe.utils.display.cli_output import emit

    runner = _validate_llm_runner()
    existing = show_topics()
    prompt = _build_prompt(existing, args.count)
    result = _call_llm(prompt, runner)
    drafts = _extract_drafts(result)
    stage_suggestions(topic_candidates=drafts, purpose_candidates=[])
    emit({"staged_topic_suggestions": drafts}, args.output)
    return ExitCode.SUCCESS
