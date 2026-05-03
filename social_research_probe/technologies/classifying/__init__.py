"""Source classification technologies.

Classifies a YouTube channel into one of four ``source_class`` buckets:
``primary`` (firsthand reporting / official channel), ``secondary``
(analysis or aggregation of primary sources), ``commentary`` (opinion,
reaction, podcast), or ``unknown`` (no signal).

Three providers are exposed:

* ``HeuristicClassifier`` — curated channel-name → class mapping; zero cost.
* ``LLMClassifier`` — prompts the active LLM runner with a structured-output
  schema; used when no curated entry exists.
* ``HybridClassifier`` — heuristic first, LLM fallback for unknowns.

Each classifier returns the enum value as a plain string. The service layer
caches results per channel within a single run.
"""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.technologies import BaseTechnology
from social_research_probe.utils.core.classifying import (
    VALID_CLASSES,
    SourceClass,
    classify_by_channel_name_signal,
    classify_by_curated_map,
    classify_by_title_signal,
    coerce_class,
)


class HeuristicClassifier(BaseTechnology[dict, SourceClass]):
    """Curated channel map plus title/name regex signals; zero cost.

    Examples:
        Input:
            HeuristicClassifier
        Output:
            HeuristicClassifier
    """

    name: ClassVar[str] = "classifying.heuristic"
    enabled_config_key: ClassVar[str] = "classifying"

    async def _execute(self, data: dict) -> SourceClass:
        """Run this component and return the project-shaped output expected by its service.

        The helper keeps a small project rule named and documented at the boundary where it is used.

        Args:
            data: Input payload at this service, technology, or pipeline boundary.

        Returns:
            Normalized value needed by the next operation.

        Examples:
            Input:
                await _execute(
                    data={"title": "Example", "url": "https://youtu.be/demo"},
                )
            Output:
                "AI safety"
        """
        channel = str(data.get("channel") or data.get("author_name") or "")
        title = str(data.get("title") or "")
        curated = classify_by_curated_map(channel)
        if curated != "unknown":
            return curated
        name_signal = classify_by_channel_name_signal(channel)
        if name_signal != "unknown":
            return name_signal
        return classify_by_title_signal(title)


_LLM_RESPONSE_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "source_class": {"type": "string", "enum": list(VALID_CLASSES)},
    },
    "required": ["source_class"],
    "additionalProperties": False,
}

_LLM_PROMPT_TEMPLATE = (
    "Classify the following YouTube channel into one of four source-type "
    "categories used in journalism research:\n"
    "- primary: original/firsthand reporting, official outlets, government or "
    "company channels.\n"
    "- secondary: analysis, explainers, aggregation of primary sources.\n"
    "- commentary: opinion, reaction, podcast, discussion, react content.\n"
    "- unknown: insufficient signal to classify.\n\n"
    "Channel: {channel}\n"
    "Sample title: {title}\n\n"
    "Reply only with the JSON object."
)


class LLMClassifier(BaseTechnology[dict, SourceClass]):
    """Asks the configured LLM runner to classify the channel into the enum.

    Examples:
        Input:
            LLMClassifier
        Output:
            LLMClassifier
    """

    name: ClassVar[str] = "classifying.llm"
    enabled_config_key: ClassVar[str] = "classifying"

    async def _execute(self, data: dict) -> SourceClass:
        """Return the execute.

        The caller gets one stable method even when this component needs fallbacks or provider-specific
        handling.

        Args:
            data: Input payload at this service, technology, or pipeline boundary.

        Returns:
            Normalized value needed by the next operation.

        Examples:
            Input:
                await _execute(
                    data={"title": "Example", "url": "https://youtu.be/demo"},
                )
            Output:
                "AI safety"
        """
        from social_research_probe.config import load_active_config
        from social_research_probe.utils.display.progress import log
        from social_research_probe.utils.llm.registry import run_with_fallback

        cfg = load_active_config()
        debug = cfg.debug_enabled("pipeline")
        runner = cfg.preferred_free_text_runner
        if runner is None:
            if debug:
                log("[TECH][classifying.llm] no runner configured")
            return "unknown"
        channel = str(data.get("channel") or data.get("author_name") or "")
        title = str(data.get("title") or "")
        prompt = _LLM_PROMPT_TEMPLATE.format(channel=channel, title=title)
        try:
            payload = run_with_fallback(prompt, schema=_LLM_RESPONSE_SCHEMA, preferred=runner)
        except Exception as exc:
            if debug:
                log(f"[TECH][classifying.llm] runner failed: {exc}")
            return "unknown"
        result = coerce_class(payload.get("source_class") if isinstance(payload, dict) else None)
        if debug:
            log(f"[TECH][classifying.llm] {channel!r} → {result}")
        return result


class HybridClassifier(BaseTechnology[dict, SourceClass]):
    """Heuristic first, LLM fallback when curated map yields ``unknown``.

    Examples:
        Input:
            HybridClassifier
        Output:
            HybridClassifier
    """

    name: ClassVar[str] = "classifying.hybrid"
    enabled_config_key: ClassVar[str] = "classifying"

    def __init__(self) -> None:
        """Store constructor options used by later method calls.

        Returns:
            None. The result is communicated through state mutation, file/database writes, output, or an
            exception.

        Examples:
            Input:
                __init__()
            Output:
                None
        """
        super().__init__()
        self._heuristic = HeuristicClassifier()
        self._llm = LLMClassifier()

    async def _execute(self, data: dict) -> SourceClass:
        """Run this component and return the project-shaped output expected by its service.

        The helper keeps a small project rule named and documented at the boundary where it is used.

        Args:
            data: Input payload at this service, technology, or pipeline boundary.

        Returns:
            Normalized value needed by the next operation.

        Examples:
            Input:
                await _execute(
                    data={"title": "Example", "url": "https://youtu.be/demo"},
                )
            Output:
                "AI safety"
        """
        result = await self._heuristic._execute(data)
        if result != "unknown":
            return result
        return await self._llm._execute(data)
