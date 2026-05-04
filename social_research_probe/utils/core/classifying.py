"""Pure classification utilities shared across layers."""

from __future__ import annotations

import re

SourceClass = str

VALID_CLASSES: tuple[str, ...] = ("primary", "secondary", "commentary", "unknown")

_CURATED_CHANNEL_MAP: tuple[tuple[str, str], ...] = (
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
    ("vox", "secondary"),
    ("wendover productions", "secondary"),
    ("real engineering", "secondary"),
    ("polymatter", "secondary"),
    ("kurzgesagt", "secondary"),
    ("johnny harris", "secondary"),
    ("cnbc", "secondary"),
    ("tldr news", "secondary"),
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
        r"\breport(s|ing)?\b",
    )
)

_SECONDARY_NAME_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\bexplain(s|ed|er)?\b",
        r"\banalys[it]s\b",
        r"\breview(s)?\b",
        r"\btech\b",
        r"\bacademy\b",
        r"\blearning\b",
        r"\btutorial(s)?\b",
    )
)

_COMMENTARY_NAME_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\bpodcast\b",
        r"\breact(s|ion)?\b",
        r"\bshow\b",
        r"\btalk(s)?\b",
        r"\brant(s)?\b",
    )
)


def classify_by_curated_map(channel: str) -> SourceClass:
    """Return the classify by curated map.

    This shared utility keeps one parsing or normalization rule in a single place instead of letting
    call sites drift apart.

    Args:
        channel: YouTube channel name, id, or classification map used for source labeling.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            classify_by_curated_map(
                channel="OpenAI",
            )
        Output:
            "AI safety"
    """
    if not channel:
        return "unknown"
    needle = channel.lower()
    for fragment, cls in _CURATED_CHANNEL_MAP:
        if fragment in needle:
            return cls
    return "unknown"


def classify_by_title_signal(title: str) -> SourceClass:
    """Return the classify by title signal.

    This shared utility keeps one parsing or normalization rule in a single place instead of letting
    call sites drift apart.

    Args:
        title: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
               to a provider.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            classify_by_title_signal(
                title="This tool reduces latency by 30%.",
            )
        Output:
            "AI safety"
    """
    if not title:
        return "unknown"
    for pattern in _COMMENTARY_TITLE_PATTERNS:
        if pattern.search(title):
            return "commentary"
    return "unknown"


def classify_by_channel_name_signal(channel: str) -> SourceClass:
    """Return the classify by channel name signal.

    This shared utility keeps one parsing or normalization rule in a single place instead of letting
    call sites drift apart.

    Args:
        channel: YouTube channel name, id, or classification map used for source labeling.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            classify_by_channel_name_signal(
                channel="OpenAI",
            )
        Output:
            "AI safety"
    """
    if not channel:
        return "unknown"
    for pattern in _PRIMARY_NAME_PATTERNS:
        if pattern.search(channel):
            return "primary"
    for pattern in _SECONDARY_NAME_PATTERNS:
        if pattern.search(channel):
            return "secondary"
    for pattern in _COMMENTARY_NAME_PATTERNS:
        if pattern.search(channel):
            return "commentary"
    return "unknown"


def coerce_class(value: object) -> SourceClass:
    """Convert an untyped value into a safe class value.

    Normalizing here keeps loosely typed external values from spreading into business logic.

    Args:
        value: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
               to a provider.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            coerce_class(
                value="42",
            )
        Output:
            "AI safety"
    """
    if isinstance(value, str) and value.lower() in VALID_CLASSES:
        return value.lower()
    return "unknown"
