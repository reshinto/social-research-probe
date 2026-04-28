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

import re
from typing import ClassVar

from social_research_probe.technologies import BaseTechnology

SourceClass = str  # one of: "primary" | "secondary" | "commentary" | "unknown"

VALID_CLASSES: tuple[str, ...] = ("primary", "secondary", "commentary", "unknown")

# Curated mapping of channel-name fragments to source class. Match is
# case-insensitive substring on the channel name. First-match wins, so order
# entries from most-specific to least-specific.
_CURATED_CHANNEL_MAP: tuple[tuple[str, str], ...] = (
    # Primary — major news outlets and official channels
    ("reuters", "primary"),
    ("associated press", "primary"),
    ("ap news", "primary"),
    ("bbc news", "primary"),
    ("cnn", "primary"),
    ("bloomberg", "primary"),
    ("wall street journal", "primary"),
    ("the new york times", "primary"),
    ("the washington post", "primary"),
    ("financial times", "primary"),
    ("the guardian", "primary"),
    ("nbc news", "primary"),
    ("cbs news", "primary"),
    ("abc news", "primary"),
    ("al jazeera", "primary"),
    ("npr", "primary"),
    ("pbs newshour", "primary"),
    ("the economist", "primary"),
    # Secondary — analysis, explainers, aggregators
    ("vox", "secondary"),
    ("wendover productions", "secondary"),
    ("real engineering", "secondary"),
    ("polymatter", "secondary"),
    ("kurzgesagt", "secondary"),
    ("johnny harris", "secondary"),
    ("cnbc", "secondary"),
    ("tldr news", "secondary"),
    # Commentary — opinion, reaction, podcasts
    ("podcast", "commentary"),
    ("reacts", "commentary"),
    ("reaction", "commentary"),
    ("hasanabi", "commentary"),
)

_COMMENTARY_TITLE_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\breact(s|ion|ing)\b",
        r"\bopinion\b",
        r"\bmy take\b",
        r"\bpodcast\b",
    )
)

_PRIMARY_NAME_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\bnews\b",
        r"\bofficial\b",
    )
)


def classify_by_curated_map(channel: str) -> SourceClass:
    """Return curated class for ``channel`` or ``"unknown"`` when no match."""
    if not channel:
        return "unknown"
    needle = channel.lower()
    for fragment, cls in _CURATED_CHANNEL_MAP:
        if fragment in needle:
            return cls
    return "unknown"


def classify_by_title_signal(title: str) -> SourceClass:
    """Return ``"commentary"`` when the title signals reaction/opinion content.

    Returns ``"unknown"`` when no commentary pattern is present, so callers
    can use this as an item-level override that does not promote primary or
    secondary classifications.
    """
    if not title:
        return "unknown"
    for pattern in _COMMENTARY_TITLE_PATTERNS:
        if pattern.search(title):
            return "commentary"
    return "unknown"


def classify_by_channel_name_signal(channel: str) -> SourceClass:
    """Return ``"primary"`` for channels whose name contains news/official tokens."""
    if not channel:
        return "unknown"
    for pattern in _PRIMARY_NAME_PATTERNS:
        if pattern.search(channel):
            return "primary"
    return "unknown"


def coerce_class(value: object) -> SourceClass:
    """Coerce arbitrary input to a valid ``source_class`` string."""
    if isinstance(value, str) and value.lower() in VALID_CLASSES:
        return value.lower()
    return "unknown"


class HeuristicClassifier(BaseTechnology[dict, SourceClass]):
    """Curated channel map plus title/name regex signals; zero cost."""

    name: ClassVar[str] = "classifying.heuristic"
    enabled_config_key: ClassVar[str] = "classifying"

    async def _execute(self, data: dict) -> SourceClass:
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
    """Asks the configured LLM runner to classify the channel into the enum."""

    name: ClassVar[str] = "classifying.llm"
    enabled_config_key: ClassVar[str] = "classifying"

    async def _execute(self, data: dict) -> SourceClass:
        from social_research_probe.config import load_active_config
        from social_research_probe.utils.llm.registry import run_with_fallback

        cfg = load_active_config()
        runner = cfg.preferred_free_text_runner
        if runner is None:
            return "unknown"
        channel = str(data.get("channel") or data.get("author_name") or "")
        title = str(data.get("title") or "")
        prompt = _LLM_PROMPT_TEMPLATE.format(channel=channel, title=title)
        try:
            payload = run_with_fallback(prompt, schema=_LLM_RESPONSE_SCHEMA, preferred=runner)
        except Exception:
            return "unknown"
        return coerce_class(payload.get("source_class") if isinstance(payload, dict) else None)


class HybridClassifier(BaseTechnology[dict, SourceClass]):
    """Heuristic first, LLM fallback when curated map yields ``unknown``."""

    name: ClassVar[str] = "classifying.hybrid"
    enabled_config_key: ClassVar[str] = "classifying"

    def __init__(self) -> None:
        super().__init__()
        self._heuristic = HeuristicClassifier()
        self._llm = LLMClassifier()

    async def _execute(self, data: dict) -> SourceClass:
        result = await self._heuristic._execute(data)
        if result != "unknown":
            return result
        return await self._llm._execute(data)
