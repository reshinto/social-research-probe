"""Re-export shim — logic lives in technologies/llms/ensemble.py."""

from social_research_probe.technologies.llms.ensemble import (  # noqa: F401
    _PROVIDERS,
    _TIMEOUT,
    _build_synthesis_prompt,
    _collect_responses,
    _llm_enabled,
    _run_provider,
    _service_enabled,
    _synthesize,
    multi_llm_prompt,
)

__all__ = ["multi_llm_prompt"]
