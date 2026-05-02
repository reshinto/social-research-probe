"""Constants for the offline demo report command.

Single source of truth for synthetic-data strings used by the demo
fixture and command. No logic, no I/O.
"""

from __future__ import annotations

DEMO_TOPIC: str = "[SYNTHETIC DEMO] AI coding agents and the future of junior developers"

DEMO_DISCLAIMER: str = (
    "Synthetic sample data for product demonstration only. Not factual market research."
)

DEMO_PURPOSE_SET: tuple[str, ...] = (
    "career strategy for early-career engineers",
    "hiring market signal for engineering managers",
    "curriculum gap analysis for bootcamp operators",
)

DEMO_THEMES: tuple[str, ...] = (
    "junior developer role compression",
    "pair-programming skill premium rising",
    "code-review competence as new senior signal",
    "AI agent reliability ceiling",
    "bootcamp curriculum churn",
)
