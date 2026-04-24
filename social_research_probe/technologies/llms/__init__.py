"""LLM technology adapters — registers all available runners on import."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class AgenticSearchCitation:
    """One citation returned by a runner's agentic search.

    Attributes:
        url: Absolute URL of the cited source. Empty string when the runner
            returned a citation without a URL (rare; caller should drop these).
        title: Human-readable title of the cited source, or empty string when
            the runner did not provide one.
    """

    url: str
    title: str = ""


@dataclass
class AgenticSearchResult:
    """Structured payload returned by every runner's ``agentic_search``.

    Runner implementations wrap their native search feature (Gemini google-search,
    Claude web_search tool, Codex ``--search``) so callers can treat them
    uniformly. The shape is intentionally narrow — enough for corroboration
    backends to apply source-quality filtering and compute a verdict.

    Attributes:
        answer: Natural-language answer synthesised by the runner.
        citations: Source URLs cited in the answer. May be empty if the runner
            produced an answer without citations; caller decides how to treat.
        runner_name: Identifier of the runner that produced the result
            (``"gemini"``, ``"claude"``, ``"codex"``). Useful for debugging and
            for logging which backend actually ran.
    """

    answer: str
    citations: list[AgenticSearchCitation] = field(default_factory=list)
    runner_name: str = ""
