"""Multi-LLM ensemble and config-aware free-text LLM routing.

When config selects Claude, Gemini, or Codex as the default runner, this module
uses that provider directly for free-text prompts. Otherwise it fans out across
Claude, Gemini, and Codex in parallel, then synthesizes the responses with the
highest-priority available provider.

Counterpart to ``llm/runners/``, which handles structured JSON-schema LLM
calls (used by corroboration). This module handles free-text prompts used
by the pipeline for summarization and any other unstructured LLM tasks.

Supported CLIs (must be installed and authenticated separately):
  - Claude Code CLI: ``claude -p "<prompt>"``
  - Gemini CLI:      ``gemini -p "<prompt>"``
  - Codex CLI:       ``codex "<prompt>"``
"""

from __future__ import annotations

import asyncio
import os

from social_research_probe.config import load_active_config
from social_research_probe.types import FreeTextRunnerName
from social_research_probe.utils.progress import log

# Seconds to wait for each provider before giving up.
_TIMEOUT = 60

# Ordered priority: Claude first for synthesis fallback.
_PROVIDERS: tuple[FreeTextRunnerName, ...] = ("claude", "gemini", "codex")


def _llm_enabled(cfg) -> bool:
    """Return True when the LLM service gate is enabled."""
    service_enabled = getattr(cfg, "service_enabled", None)
    if callable(service_enabled):
        return bool(service_enabled("llm"))
    return True


async def _run_provider(name: str, prompt: str, task: str = "generating response") -> str | None:
    """Call one LLM CLI subprocess asynchronously; return stripped stdout or None on failure.

    Silently catches all exceptions so a missing or rate-limited CLI never
    crashes the caller — it simply contributes nothing to the ensemble.
    """
    log(f"[srp] LLM ({name}): {task}")
    try:
        stdin_data: bytes | None = None
        if name == "claude":
            cmd = ["claude", "-p", prompt]
        elif name == "gemini":
            cmd = ["gemini", "-p", prompt]
        elif name == "codex":
            cmd = ["codex", "exec", prompt]
        elif name == "local":
            bin_path = os.environ.get("SRP_LOCAL_LLM_BIN", "")
            if not bin_path:
                return None
            cmd = [bin_path]
            stdin_data = prompt.encode()
        else:
            return None

        stdin = asyncio.subprocess.PIPE if stdin_data is not None else asyncio.subprocess.DEVNULL
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=stdin,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        try:
            stdout, _ = await asyncio.wait_for(proc.communicate(stdin_data), timeout=_TIMEOUT)
        except TimeoutError:
            proc.kill()
            await proc.wait()
            return None
        output = stdout.decode().strip()
        return output if output else None
    except Exception:
        return None


async def _collect_responses(
    prompt: str,
    task: str = "generating response",
    providers: tuple[FreeTextRunnerName, ...] = _PROVIDERS,
) -> dict[str, str]:
    """Fan out the prompt to all providers concurrently via asyncio.gather.

    Returns a dict mapping provider name to response text for every provider
    that succeeded. Missing or failed providers are absent from the dict.
    """
    if not providers:
        return {}
    results = await asyncio.gather(
        *[_run_provider(name, prompt, task) for name in providers],
        return_exceptions=True,
    )
    return {
        name: resp
        for name, resp in zip(providers, results, strict=True)
        if isinstance(resp, str) and resp
    }


def _build_synthesis_prompt(original_prompt: str, responses: dict[str, str]) -> str:
    """Construct a meta-prompt instructing the synthesizer to merge all responses."""
    blocks = "\n\n".join(f"[Response {i + 1}]\n{text}" for i, text in enumerate(responses.values()))
    return (
        "You received these responses from multiple AI assistants answering the same request. "
        "Synthesize them into one comprehensive, well-organized answer that captures the best "
        "insights from all responses. Do not mention how many assistants responded or label "
        "individual responses.\n\n"
        f"Original request:\n{original_prompt}\n\n"
        f"Responses to synthesize:\n{blocks}"
    )


async def _synthesize(responses: dict[str, str], original_prompt: str, cfg=None) -> str | None:
    """Produce the final answer from collected responses.

    If only one provider responded, returns it directly.
    Otherwise uses Claude → Gemini → Codex to synthesize all responses.
    Falls back to the best available single response if synthesis also fails.
    Providers disabled via ``<name>_service_enabled`` are skipped unless they
    are the configured primary runner.
    """
    if not responses:
        return None
    if len(responses) == 1:
        return next(iter(responses.values()))

    synthesis_prompt = _build_synthesis_prompt(original_prompt, responses)
    synth_providers = (
        tuple(p for p in _PROVIDERS if _service_enabled(cfg, p)) if cfg is not None else _PROVIDERS
    )
    for provider in synth_providers:
        result = await _run_provider(
            provider, synthesis_prompt, task="synthesising ensemble responses"
        )
        if result:
            return result

    # All synthesis attempts failed — return best single response by priority.
    return responses.get("claude") or responses.get("gemini") or responses.get("codex")


def _service_enabled(cfg, provider: str) -> bool:
    """Return True iff provider is allowed to run as a non-primary service.

    The primary runner is always allowed; secondary providers are gated by
    their technology flags so users can disable one provider without
    disabling the rest of the LLM service.
    """
    if not _llm_enabled(cfg):
        return False
    technology_enabled = getattr(cfg, "technology_enabled", None)
    if callable(technology_enabled):
        return bool(technology_enabled(provider))
    if cfg.llm_runner == provider:
        return True
    return True


async def multi_llm_prompt(prompt: str, task: str = "generating response") -> str | None:
    """Run a free-text prompt through the configured default runner or ensemble.

    When runner is ``none``, returns None immediately without calling any LLM.
    When a specific provider is configured, that provider is used directly.
    Falls back to the ensemble fan-out only if preferred_free_text_runner
    returns None for an unrecognised runner value.
    """
    cfg = load_active_config()
    if not _llm_enabled(cfg):
        return None
    if cfg.llm_runner == "none":
        return None
    preferred = cfg.preferred_free_text_runner
    if preferred is not None:
        preferred_result = await _run_provider(preferred, prompt, task)
        if preferred_result:
            return preferred_result
        candidates = (
            _PROVIDERS if preferred == "local" else tuple(p for p in _PROVIDERS if p != preferred)
        )
        providers = tuple(p for p in candidates if _service_enabled(cfg, p))
        responses = await _collect_responses(prompt, task, providers=providers)
        return await _synthesize(responses, prompt, cfg)
    providers = tuple(p for p in _PROVIDERS if _service_enabled(cfg, p))
    responses = await _collect_responses(prompt, task, providers=providers)
    return await _synthesize(responses, prompt, cfg)
