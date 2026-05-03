"""Command: suggest-purposes. Generate and stage new purpose suggestions via LLM."""

from __future__ import annotations

import argparse

from social_research_probe.utils.core.exit_codes import ExitCode


def _validate_llm_runner() -> str:
    """Return the configured runner or raise if disabled.

    Command helpers keep user-facing parsing, validation, and output formatting out of the pipeline
    and service layers.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _validate_llm_runner()
        Output:
            "codex"
    """
    from social_research_probe.config import load_active_config
    from social_research_probe.utils.core.errors import ValidationError

    cfg = load_active_config()
    if cfg.default_structured_runner == "none":
        raise ValidationError("suggest-purposes requires an LLM runner (set llm.runner in config)")
    return cfg.default_structured_runner


def _build_prompt(existing: list[str], count: int) -> str:
    """Format the suggest-purposes LLM prompt.

    Command helpers keep user-facing parsing, validation, and output formatting out of the pipeline
    and service layers.

    Args:
        existing: Intermediate collection used to preserve ordering while stage results are merged.
        count: Count, database id, index, or limit that bounds the work being performed.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _build_prompt(
                existing=[],
                count=3,
            )
        Output:
            "AI safety"
    """
    from social_research_probe.utils.llm.prompts import SUGGEST_PURPOSES_PROMPT

    return SUGGEST_PURPOSES_PROMPT.format(
        existing_purposes=", ".join(existing) if existing else "(none yet)",
        count=count,
    )


def _call_llm(prompt: str, runner: str) -> dict:
    """Call the LLM and return the raw result dict.

    Command helpers keep user-facing parsing, validation, and output formatting out of the pipeline
    and service layers.

    Args:
        prompt: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
                to a provider.
        runner: LLM runner name or runner instance selected for the request.

    Returns:
        Dictionary with stable keys consumed by downstream project code.

    Examples:
        Input:
            _call_llm(
                prompt="Summarize this source.",
                runner="AI safety",
            )
        Output:
            {"enabled": True}
    """
    from social_research_probe.utils.llm.registry import run_with_fallback
    from social_research_probe.utils.llm.schemas import PURPOSE_SUGGESTIONS_SCHEMA

    return run_with_fallback(prompt, PURPOSE_SUGGESTIONS_SCHEMA, runner)


def _extract_drafts(result: dict) -> list[dict]:
    """Extract purpose suggestion dicts from the LLM result.

    Command helpers keep user-facing parsing, validation, and output formatting out of the pipeline
    and service layers.

    Args:
        result: Service or technology result being inspected for payload and diagnostics.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            _extract_drafts(
                result=ServiceResult(service_name="comments", input_key="demo", tech_results=[]),
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
    """
    return [{"name": s["name"], "method": s["method"]} for s in result.get("suggestions", [])]


def run(args: argparse.Namespace) -> int:
    """Build the small payload that carries staged_purpose_suggestions through this workflow.

    This is the command boundary: argparse passes raw options in, and the rest of the application
    receives validated project data or a clear error.

    Args:
        args: Parsed argparse namespace for the command being dispatched.

    Returns:
        Integer count, limit, status code, or timeout used by the caller.

    Examples:
        Input:
            run(
                args=argparse.Namespace(output="json"),
            )
        Output:
            5
    """
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
