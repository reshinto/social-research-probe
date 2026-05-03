"""Search query support.

It centralizes shared rules that would otherwise be copied across services, commands, and reports.
"""

_QUERY_STOPWORDS = frozenset(
    {
        "the",
        "a",
        "an",
        "of",
        "for",
        "to",
        "and",
        "or",
        "in",
        "on",
        "with",
        "get",
        "my",
        "by",
        "via",
        "from",
        "about",
        "how",
        "what",
        "which",
        "track",
        "latest",
        "across",
        "channels",
        "velocity",
        "saturation",
        "emergence",
    }
)


def enrich_query(topic: str, method: str) -> str:
    """Append up to 3 meaningful method keywords to the search topic.

    This utility is shared across commands, services, and stages, so the rule lives here instead of
    being reimplemented differently at each call site.

    Args:
        topic: Research topic text or existing topic list used for classification and suggestions.
        method: Purpose method text that explains how the research should be evaluated.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            enrich_query(
                topic="AI safety",
                method="Find unmet needs",
            )
        Output:
            "AI safety"
    """
    words = [w for w in method.lower().split() if w not in _QUERY_STOPWORDS and len(w) > 2][:3]
    extra = " ".join(dict.fromkeys(words))
    return f"{topic} {extra}".strip() if extra else topic
