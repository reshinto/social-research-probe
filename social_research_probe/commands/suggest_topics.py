"""Command: suggest-topics. Generate and stage new topic suggestions via LLM."""

from __future__ import annotations

import argparse

from social_research_probe.utils.core.exit_codes import ExitCode


def run(args: argparse.Namespace) -> int:
    from social_research_probe.commands import show_topics, stage_suggestions
    from social_research_probe.config import load_active_config
    from social_research_probe.services.llm.prompts import SUGGEST_TOPICS_PROMPT
    from social_research_probe.services.llm.registry import run_with_fallback
    from social_research_probe.services.llm.schemas import TOPIC_SUGGESTIONS_SCHEMA
    from social_research_probe.utils.core.errors import ValidationError
    from social_research_probe.utils.display.cli_output import emit

    cfg = load_active_config()
    if cfg.default_structured_runner == "none":
        raise ValidationError("suggest-topics requires an LLM runner (set llm.runner in config)")

    existing = show_topics()
    prompt = SUGGEST_TOPICS_PROMPT.format(
        existing_topics=", ".join(existing) if existing else "(none yet)",
        count=args.count,
    )
    result = run_with_fallback(prompt, TOPIC_SUGGESTIONS_SCHEMA, cfg.default_structured_runner)
    drafts = [{"value": s["value"], "reason": s.get("reason", "")} for s in result.get("suggestions", [])]
    stage_suggestions(topic_candidates=drafts, purpose_candidates=[])
    emit({"staged_topic_suggestions": drafts}, args.output)
    return ExitCode.SUCCESS
