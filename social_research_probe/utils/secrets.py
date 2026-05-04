"""Helpers for resolving corroboration secrets at runtime.

Corroboration providers should behave like the platform adapters: prefer an
explicit environment override, but also work when operators stored secrets via
``srp config set-secret`` in the active data dir.
"""

from __future__ import annotations

from social_research_probe import __version__
from social_research_probe.commands.config import read_secret

# Sent as User-Agent on all outbound corroboration HTTP requests so API
# providers see an identifiable client rather than the default
# "Python-urllib/3.x" signature (which Cloudflare-fronted APIs like Exa block).
HTTP_USER_AGENT = (
    f"social-research-probe/{__version__} (+https://github.com/reshinto/social-research-probe)"
)


def read_runtime_secret(name: str) -> str | None:
    """Return a secret from env or the active secrets file.

    This utility is shared across commands, services, and stages, so the rule lives here instead of
    being reimplemented differently at each call site.

    Args:
        name: Registry, config, or CLI name used to select the matching project value.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            read_runtime_secret(
                name="AI safety",
            )
        Output:
            "AI safety"
    """
    return read_secret(name)
