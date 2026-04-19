"""Helpers for resolving corroboration secrets at runtime.

Corroboration backends should behave like the platform adapters: prefer an
explicit environment override, but also work when operators stored secrets via
``srp config set-secret`` in the active data dir.
"""

from __future__ import annotations

from social_research_probe.commands.config import read_secret
from social_research_probe.config import resolve_data_dir


def read_runtime_secret(name: str) -> str | None:
    """Return a secret from env or the active secrets file."""
    return read_secret(resolve_data_dir(None), name)
