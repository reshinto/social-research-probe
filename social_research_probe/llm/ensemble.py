"""Multi-LLM ensemble — the single place for all free-text LLM calls.

Queries Claude, Gemini, and Codex CLIs in parallel for any given prompt.
Uses Claude to synthesize all collected responses into a single final answer.
If Claude's synthesis fails, falls back to Gemini, then Codex.

Counterpart to ``llm/runners/``, which handles structured JSON-schema LLM
calls (used by corroboration). This module handles free-text prompts used
by the pipeline for summarization and any other unstructured LLM tasks.

Supported CLIs (must be installed and authenticated separately):
  - Claude Code CLI: ``claude -p "<prompt>"``
  - Gemini CLI:      ``gemini -p "<prompt>"``
  - Codex CLI:       ``codex "<prompt>"``
"""

from __future__ import annotations

import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

# Seconds to wait for each provider before giving up.
_TIMEOUT = 60

# Ordered priority: Claude first for synthesis fallback.
_PROVIDERS = ("claude", "gemini", "codex")


def _run_provider(name: str, prompt: str) -> str | None:
    """Call one LLM CLI and return its stripped stdout, or None on any failure.

    Silently catches all exceptions so a missing or rate-limited CLI never
    crashes the caller — it simply contributes nothing to the ensemble.
    """
    try:
        if name == "claude":
            result = subprocess.run(
                ["claude", "-p", prompt],
                capture_output=True,
                text=True,
                timeout=_TIMEOUT,
            )
        elif name == "gemini":
            result = subprocess.run(
                ["gemini", "-p", prompt],
                capture_output=True,
                text=True,
                timeout=_TIMEOUT,
            )
        elif name == "codex":
            result = subprocess.run(
                ["codex", prompt],
                capture_output=True,
                text=True,
                timeout=_TIMEOUT,
            )
        else:
            return None
        output = result.stdout.strip()
        return output if output else None
    except Exception:
        return None


def _collect_responses(prompt: str) -> dict[str, str]:
    """Fan out the prompt to all providers in parallel.

    Returns a dict mapping provider name to response text for every provider
    that succeeded. Missing or failed providers are absent from the dict.
    """
    responses: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=len(_PROVIDERS)) as pool:
        futures = {pool.submit(_run_provider, name, prompt): name for name in _PROVIDERS}
        for future in as_completed(futures):
            name = futures[future]
            response = future.result()
            if response:
                responses[name] = response
    return responses


def _build_synthesis_prompt(original_prompt: str, responses: dict[str, str]) -> str:
    """Construct a meta-prompt instructing the synthesizer to merge all responses."""
    blocks = "\n\n".join(
        f"[Response {i + 1}]\n{text}" for i, text in enumerate(responses.values())
    )
    return (
        "You received these responses from multiple AI assistants answering the same request. "
        "Synthesize them into one comprehensive, well-organized answer that captures the best "
        "insights from all responses. Do not mention how many assistants responded or label "
        "individual responses.\n\n"
        f"Original request:\n{original_prompt}\n\n"
        f"Responses to synthesize:\n{blocks}"
    )


def _synthesize(responses: dict[str, str], original_prompt: str) -> str | None:
    """Produce the final answer from collected responses.

    If only one provider responded, returns it directly.
    Otherwise uses Claude → Gemini → Codex to synthesize all responses.
    Falls back to the best available single response if synthesis also fails.
    """
    if not responses:
        return None
    if len(responses) == 1:
        return next(iter(responses.values()))

    synthesis_prompt = _build_synthesis_prompt(original_prompt, responses)
    for provider in _PROVIDERS:
        result = _run_provider(provider, synthesis_prompt)
        if result:
            return result

    # All synthesis attempts failed — return best single response by priority.
    return responses.get("claude") or responses.get("gemini") or responses.get("codex")


def multi_llm_prompt(prompt: str) -> str | None:
    """Query Claude, Gemini, and Codex in parallel; synthesize with Claude.

    Fallback chain for synthesis: Claude → Gemini → Codex.
    Returns None only if every provider fails at both query and synthesis.
    """
    responses = _collect_responses(prompt)
    return _synthesize(responses, prompt)
