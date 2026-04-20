"""Corroboration package — backends that check whether a claim is supported by external sources.

Import the built-in backend modules at package import time so the registry is
populated before callers ask for ``get_backend()`` or ``list_backends()``.
"""

from __future__ import annotations

import importlib
import os

for _module in (
    "social_research_probe.corroboration.brave",
    "social_research_probe.corroboration.exa",
    "social_research_probe.corroboration.llm_cli",
    "social_research_probe.corroboration.tavily",
):
    importlib.import_module(_module)

if os.environ.get("SRP_TEST_USE_FAKE_CORROBORATION") == "1":
    importlib.import_module("tests.fixtures.fake_corroboration")
