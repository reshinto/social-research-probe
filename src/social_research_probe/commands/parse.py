"""Recursive-descent parser for the srp command DSL. Never consults an LLM."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Union

from social_research_probe.errors import SrpError


class ParseError(SrpError):
    exit_code = 2


# --- AST ---------------------------------------------------------------------

@dataclass(frozen=True)
class ParsedUpdateTopics:
    op: Literal["add", "remove", "rename"]
    values: list[str] = field(default_factory=list)
    rename_from: str | None = None
    rename_to: str | None = None


@dataclass(frozen=True)
class ParsedShowTopics:
    pass


@dataclass(frozen=True)
class ParsedUpdatePurposes:
    op: Literal["add", "remove", "rename"]
    name: str | None = None
    method: str | None = None
    values: list[str] = field(default_factory=list)
    rename_from: str | None = None
    rename_to: str | None = None


@dataclass(frozen=True)
class ParsedShowPurposes:
    pass


@dataclass(frozen=True)
class ParsedSuggestTopics:
    pass


@dataclass(frozen=True)
class ParsedSuggestPurposes:
    pass


@dataclass(frozen=True)
class ParsedShowPending:
    pass


@dataclass(frozen=True)
class ParsedApplyPending:
    topic_ids: Union[Literal["all"], list[int]]
    purpose_ids: Union[Literal["all"], list[int]]


@dataclass(frozen=True)
class ParsedDiscardPending:
    topic_ids: Union[Literal["all"], list[int]]
    purpose_ids: Union[Literal["all"], list[int]]


@dataclass(frozen=True)
class ParsedRunResearch:
    platform: str
    topics: list[tuple[str, list[str]]]  # [(topic, [purpose, ...]), ...]


Parsed = Union[
    ParsedUpdateTopics,
    ParsedShowTopics,
    ParsedUpdatePurposes,
    ParsedShowPurposes,
    ParsedSuggestTopics,
    ParsedSuggestPurposes,
    ParsedShowPending,
    ParsedApplyPending,
    ParsedDiscardPending,
    ParsedRunResearch,
]


# --- Lexer helpers -----------------------------------------------------------

def _take_quoted(src: str, pos: int) -> tuple[str, int]:
    if pos >= len(src) or src[pos] != '"':
        raise ParseError(f"expected '\"' at position {pos}")
    end = src.find('"', pos + 1)
    if end == -1:
        raise ParseError("unterminated quoted string")
    return src[pos + 1 : end], end + 1


def _parse_quoted_list(src: str) -> list[str]:
    # Parse "a"|"b"|"c"
    values: list[str] = []
    pos = 0
    while pos < len(src):
        val, pos = _take_quoted(src, pos)
        values.append(val)
        if pos < len(src):
            if src[pos] != "|":
                raise ParseError(f"expected '|' or end at position {pos} in {src!r}")
            pos += 1
    return values


def _parse_id_selector(src: str) -> Union[Literal["all"], list[int]]:
    if src == "all":
        return "all"
    try:
        return [int(x.strip()) for x in src.split(",") if x.strip()]
    except ValueError as exc:
        raise ParseError(f"invalid id selector: {src!r}") from exc


# --- Command dispatch --------------------------------------------------------

def parse(text: str) -> Parsed:
    text = text.strip()
    if not text:
        raise ParseError("empty command")

    head, _, tail = text.partition(" ")
    tail = tail.strip()

    dispatch = {
        "update-topics": _parse_update_topics,
        "show-topics": lambda _: ParsedShowTopics(),
        "update-purposes": _parse_update_purposes,
        "show-purposes": lambda _: ParsedShowPurposes(),
        "suggest-topics": lambda _: ParsedSuggestTopics(),
        "suggest-purposes": lambda _: ParsedSuggestPurposes(),
        "show-pending-suggestions": lambda _: ParsedShowPending(),
        "apply-pending-suggestions": _parse_apply_pending,
        "discard-pending-suggestions": _parse_discard_pending,
        "run-research": _parse_run_research,
    }
    if head not in dispatch:
        raise ParseError(f"unknown command: {head!r}")
    return dispatch[head](tail)


def _parse_update_topics(tail: str) -> ParsedUpdateTopics:
    if tail.startswith("add:"):
        return ParsedUpdateTopics(op="add", values=_parse_quoted_list(tail[4:]))
    if tail.startswith("remove:"):
        return ParsedUpdateTopics(op="remove", values=_parse_quoted_list(tail[7:]))
    if tail.startswith("rename:"):
        rest = tail[7:]
        old, pos = _take_quoted(rest, 0)
        if rest[pos : pos + 2] != "->":
            raise ParseError("expected '->' in rename")
        new, _ = _take_quoted(rest, pos + 2)
        return ParsedUpdateTopics(op="rename", rename_from=old, rename_to=new)
    raise ParseError(f"expected add:/remove:/rename:, got {tail!r}")


def _parse_update_purposes(tail: str) -> ParsedUpdatePurposes:
    if tail.startswith("add:"):
        rest = tail[4:]
        name, pos = _take_quoted(rest, 0)
        if rest[pos : pos + 2] != '="':
            raise ParseError("expected '=' followed by quoted method")
        method, _ = _take_quoted(rest, pos + 1)
        return ParsedUpdatePurposes(op="add", name=name, method=method)
    if tail.startswith("remove:"):
        return ParsedUpdatePurposes(op="remove", values=_parse_quoted_list(tail[7:]))
    if tail.startswith("rename:"):
        rest = tail[7:]
        old, pos = _take_quoted(rest, 0)
        if rest[pos : pos + 2] != "->":
            raise ParseError("expected '->' in rename")
        new, _ = _take_quoted(rest, pos + 2)
        return ParsedUpdatePurposes(op="rename", rename_from=old, rename_to=new)
    raise ParseError(f"expected add:/remove:/rename:, got {tail!r}")


def _parse_apply_pending(tail: str) -> ParsedApplyPending:
    topic_ids, purpose_ids = _parse_pending_selectors(tail)
    return ParsedApplyPending(topic_ids=topic_ids, purpose_ids=purpose_ids)


def _parse_discard_pending(tail: str) -> ParsedDiscardPending:
    topic_ids, purpose_ids = _parse_pending_selectors(tail)
    return ParsedDiscardPending(topic_ids=topic_ids, purpose_ids=purpose_ids)


def _parse_pending_selectors(tail: str) -> tuple[Union[Literal["all"], list[int]], Union[Literal["all"], list[int]]]:
    parts = dict(_kv_pair(chunk) for chunk in tail.split())
    if "topics" not in parts or "purposes" not in parts:
        raise ParseError("apply/discard requires topics:... and purposes:...")
    return _parse_id_selector(parts["topics"]), _parse_id_selector(parts["purposes"])


def _kv_pair(chunk: str) -> tuple[str, str]:
    key, _, val = chunk.partition(":")
    if not val:
        raise ParseError(f"expected key:value, got {chunk!r}")
    return key, val


def _parse_run_research(tail: str) -> ParsedRunResearch:
    if not tail.startswith("platform:"):
        raise ParseError("run-research must start with platform:NAME")
    rest = tail[len("platform:") :]
    platform_name, _, topic_section = rest.partition(" ")
    if not platform_name or not topic_section:
        raise ParseError("run-research expects 'platform:NAME <topic>->p1+p2;...'")

    topics: list[tuple[str, list[str]]] = []
    for entry in topic_section.split(";"):
        entry = entry.strip()
        if not entry:
            continue
        topic, pos = _take_quoted(entry, 0)
        if entry[pos : pos + 2] != "->":
            raise ParseError(f"expected '->' after topic in {entry!r}")
        purposes = [p.strip() for p in entry[pos + 2 :].split("+") if p.strip()]
        if not purposes:
            raise ParseError(f"topic {topic!r} has no purposes")
        topics.append((topic, purposes))

    if not topics:
        raise ParseError("run-research needs at least one topic")
    return ParsedRunResearch(platform=platform_name, topics=topics)
