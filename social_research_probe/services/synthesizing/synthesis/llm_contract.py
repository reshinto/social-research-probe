"""Re-export shim — logic lives in technologies/synthesizing/llm_contract.py."""

from social_research_probe.technologies.synthesizing.llm_contract import (
    SYNTHESIS_JSON_SCHEMA,
    build_synthesis_prompt,
    parse_synthesis_response,
)

__all__ = ["SYNTHESIS_JSON_SCHEMA", "build_synthesis_prompt", "parse_synthesis_response"]
