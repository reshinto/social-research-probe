"""Command: suggest-purposes. Generate and stage new purpose suggestions via LLM."""

from __future__ import annotations

import argparse

from social_research_probe.utils.core.exit_codes import ExitCode


def run(args: argparse.Namespace) -> int:
    from social_research_probe.commands import show_purposes, stage_suggestions
    from social_research_probe.config import load_active_config
    from social_research_probe.services.llm.prompts import SUGGEST_PURPOSES_PROMPT
    from social_research_probe.services.llm.registry import run_with_fallback
    from social_research_probe.services.llm.schemas import PURPOSE_SUGGESTIONS_SCHEMA
    from social_research_probe.utils.core.errors import ValidationError
    from social_research_probe.utils.display.cli_output import emit

    cfg = load_active_config()
    if cfg.default_structured_runner == "none":
        raise ValidationError("suggest-purposes requires an LLM runner (set llm.runner in config)")

    existing = list(show_purposes().keys())
    prompt = SUGGEST_PURPOSES_PROMPT.format(
        existing_purposes=", ".join(existing) if existing else "(none yet)",
        count=args.count,
    )
    result = run_with_fallback(prompt, PURPOSE_SUGGESTIONS_SCHEMA, cfg.default_structured_runner)
    drafts = [{"name": s["name"], "method": s["method"]} for s in result.get("suggestions", [])]
    stage_suggestions(topic_candidates=[], purpose_candidates=drafts)
    emit({"staged_purpose_suggestions": drafts}, args.output)
    return ExitCode.SUCCESS
