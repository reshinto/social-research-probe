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
    """Return the configured runner or ``None`` when LLM is disabled.

    Command helpers keep user-facing parsing, validation, and output formatting out of the pipeline
    and service layers.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            _resolve_runner_or_none()
        Output:
            "AI safety"
    """
    from social_research_probe.config import load_active_config

    runner = load_active_config().default_structured_runner
    return None if runner == "none" else runner


def _seed_drafts(existing: list[str], count: int) -> list[dict]:
    """Pick deterministic seed topics not already present.

    Command helpers keep user-facing parsing, validation, and output formatting out of the pipeline
    and service layers.

    Args:
        existing: Intermediate collection used to preserve ordering while stage results are merged.
        count: Count, database id, index, or limit that bounds the work being performed.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            _seed_drafts(
                existing=[],
                count=3,
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
    """
    candidates = [t for t in _TOPIC_SEED_POOL if t not in set(existing)]
    return [
        {"value": v, "reason": "seed pool (no LLM runner configured)"} for v in candidates[:count]
    ]


def _build_prompt(existing: list[str], count: int) -> str:
    """Format the suggest-topics LLM prompt.

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
    from social_research_probe.utils.llm.prompts import SUGGEST_TOPICS_PROMPT

    return SUGGEST_TOPICS_PROMPT.format(
        existing_topics=", ".join(existing) if existing else "(none yet)",
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
    from social_research_probe.utils.llm.schemas import TOPIC_SUGGESTIONS_SCHEMA

    return run_with_fallback(prompt, TOPIC_SUGGESTIONS_SCHEMA, runner)


def _extract_drafts(result: dict) -> list[dict]:
    """Extract topic suggestion dicts from the LLM result.

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
    return [
        {"value": s["value"], "reason": s.get("reason", "")} for s in result.get("suggestions", [])
    ]


def run(args: argparse.Namespace) -> int:
    """Build the small payload that carries staged_topic_suggestions through this workflow.

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
