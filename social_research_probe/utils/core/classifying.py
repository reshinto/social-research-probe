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
    """Return curated class for ``channel`` or ``"unknown"`` when no match."""
    if not channel:
        return "unknown"
    needle = channel.lower()
    for fragment, cls in _CURATED_CHANNEL_MAP:
        if fragment in needle:
            return cls
    return "unknown"


def classify_by_title_signal(title: str) -> SourceClass:
    """Return ``"commentary"`` when the title signals reaction/opinion content."""
    if not title:
        return "unknown"
    for pattern in _COMMENTARY_TITLE_PATTERNS:
        if pattern.search(title):
            return "commentary"
    return "unknown"


def classify_by_channel_name_signal(channel: str) -> SourceClass:
    """Return a class when channel name contains recognisable tokens."""
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
    """Coerce arbitrary input to a valid ``source_class`` string."""
    if isinstance(value, str) and value.lower() in VALID_CLASSES:
        return value.lower()
    return "unknown"
