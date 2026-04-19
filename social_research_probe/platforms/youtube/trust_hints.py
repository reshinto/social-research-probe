"""Channel-level trust signals: age, verified, subs, citation markers."""

from __future__ import annotations

import re
from datetime import UTC, datetime

_URL_RE = re.compile(r"https?://\S+")


def account_age_days(created_iso: str | None) -> int | None:
    if not created_iso:
        return None
    created = datetime.fromisoformat(created_iso.replace("Z", "+00:00"))
    return (datetime.now(UTC) - created).days


def citation_markers(description: str | None) -> list[str]:
    if not description:
        return []
    return _URL_RE.findall(description)
