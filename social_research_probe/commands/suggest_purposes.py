"""Command: suggest-purposes. Generate and stage new purpose suggestions via LLM."""

from __future__ import annotations

import argparse

from social_research_probe.utils.core.exit_codes import ExitCode


def _validate_llm_runner() -> str:
    """Return the configured runner or raise if disabled."""
    from social_research_probe.config import load_active_config
    from social_research_probe.utils.core.errors import ValidationError

    cfg = load_active_config()
    if cfg.default_structured_runner == "none":
        raise ValidationError("suggest-purposes requires an LLM runner (set llm.runner in config)")
    return cfg.default_structured_runner


def _build_prompt(existing: list[str], count: int) -> str:
    """Format the suggest-purposes LLM prompt."""
    from social_research_probe.utils.llm.prompts import SUGGEST_PURPOSES_PROMPT

    return SUGGEST_PURPOSES_PROMPT.format(
        existing_purposes=", ".join(existing) if existing else "(none yet)",
        count=count,
    )


def _call_llm(prompt: str, runner: str) -> dict:
    """Call the LLM and return the raw result dict."""
    from social_research_probe.utils.llm.registry import run_with_fallback
    from social_research_probe.utils.llm.schemas import PURPOSE_SUGGESTIONS_SCHEMA

    return run_with_fallback(prompt, PURPOSE_SUGGESTIONS_SCHEMA, runner)


def _extract_drafts(result: dict) -> list[dict]:
    """Extract purpose suggestion dicts from the LLM result."""
    return [{"name": s["name"], "method": s["method"]} for s in result.get("suggestions", [])]


def run(args: argparse.Namespace) -> int:
    from social_research_probe.commands import add_pending_suggestions, list_purposes
    from social_research_probe.utils.display.cli_output import emit

    runner = _validate_llm_runner()
    existing = list(list_purposes().keys())
    prompt = _build_prompt(existing, args.count)
    result = _call_llm(prompt, runner)
    drafts = _extract_drafts(result)
    add_pending_suggestions(topic_candidates=[], purpose_candidates=drafts)
    emit({"staged_purpose_suggestions": drafts}, args.output)
    return ExitCode.SUCCESS
