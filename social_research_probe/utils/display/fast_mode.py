"""Fast-mode env-var gate for first-run latency optimisations.

Fast mode trades a small amount of quality for speed on first-run (cache-miss)
research calls. When ``SRP_FAST_MODE`` is set to a truthy value the pipeline:

- Skips the runner-direct URL summary path (no vision/media LLM call).
- Skips merged-summary reconciliation (returns the text summary directly).
- Caps the per-run enrichment cutoff at :data:`FAST_MODE_TOP_N` items.
- Limits corroboration to the first available provider only.

Repeat runs already pay near-zero cost thanks to the pipeline cache, so fast
mode is primarily useful for fresh topics where end-to-end latency matters
more than multi-signal synthesis.
"""

from __future__ import annotations

import os

_TRUTHY = {"1", "true", "yes", "on"}

# Hard caps applied when fast mode is active. Tuned for the `latest-news`
# style one-shot queries where a shallower but faster answer is preferred.
FAST_MODE_TOP_N = 3
FAST_MODE_MAX_PROVIDERS = 1


def fast_mode_enabled() -> bool:
    """Return True iff ``SRP_FAST_MODE`` env var selects the fast pipeline."""
    return os.environ.get("SRP_FAST_MODE", "").strip().lower() in _TRUTHY
