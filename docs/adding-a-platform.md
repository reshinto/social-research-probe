[Home](README.md) → Adding a Platform

# Adding a New Platform

This guide walks through adding a new content source (e.g. TikTok, Reddit, Twitter/X, Bluesky, RSS feeds) alongside the existing YouTube adapter. By the end you will be able to run:

```bash
srp research tiktok "AI safety" "latest-news"
```

The pipeline, scoring, statistics, charts, and report generation are all platform-agnostic. You only have to implement the adapter.

![Workflow for adding a new platform adapter](diagrams/add_platform_flow.svg)

---

## Architecture in one paragraph

Every content source is a **platform adapter** — a class that knows how to search its source, hydrate results with metrics, and expose trust signals. The pipeline calls your adapter via a shared interface ([`PlatformAdapter`](../social_research_probe/platforms/base.py)) and never knows which platform it is talking to. Registration happens at import time via the `@register` decorator, so adding a platform is a matter of creating a new subpackage and implementing six methods.

---

## The adapter contract

Your adapter must subclass [`PlatformAdapter`](../social_research_probe/platforms/base.py) and implement these six methods:

| Method | What it does | Called in stage |
|---|---|---|
| `health_check() -> bool` | Return True if the adapter can run (API keys present, etc.) | Pre-flight |
| `search(topic, limits) -> list[RawItem]` | Query the source and return a list of normalised items | 1 (Fetch) |
| `async enrich(items) -> list[RawItem]` | Add metrics (views, likes, author stats) to each item | 1 (Fetch) |
| `to_signals(items) -> list[SignalSet]` | Derive per-item numeric signals used by the scorer | 2 (Score) |
| `trust_hints(item) -> TrustHints` | Extract trust metadata for one item | 2 (Score) |
| `url_normalize(url) -> str` | Return a canonical URL for deduplication | 2 (Score) |

Plus two class-level attributes:

```python
name: ClassVar[str] = "tiktok"                     # the registry key
default_limits: ClassVar[FetchLimits] = FetchLimits(max_items=50, recency_days=90)
```

Optionally, override `fetch_text_for_claim_extraction(item)` to supply text (e.g. a caption or description) for the corroboration stage. Default returns `None`.

![How the adapter methods plug into the pipeline](diagrams/add_platform_contract.svg)

---

## Step-by-step walkthrough

### Step 1 — Create the subpackage

```bash
mkdir -p social_research_probe/platforms/tiktok
touch social_research_probe/platforms/tiktok/__init__.py
touch social_research_probe/platforms/tiktok/adapter.py
touch social_research_probe/platforms/tiktok/fetch.py    # your HTTP/API calls
```

### Step 2 — Wire the subpackage into the registry

`social_research_probe/platforms/tiktok/__init__.py`:

```python
"""Importing this subpackage registers the TikTokAdapter."""

from social_research_probe.platforms.tiktok.adapter import TikTokAdapter

__all__ = ["TikTokAdapter"]
```

`social_research_probe/platforms/__init__.py` — add one import line so the adapter is registered at package load:

```python
import social_research_probe.platforms.youtube.adapter
import social_research_probe.platforms.tiktok.adapter
```

### Step 3 — Implement the adapter

Copy the structure of [`platforms/youtube/adapter.py`](../social_research_probe/platforms/youtube/adapter.py) and adapt. Minimal skeleton:

```python
from __future__ import annotations

from datetime import UTC, datetime
from typing import ClassVar

from social_research_probe.platforms.base import (
    FetchLimits,
    PlatformAdapter,
    RawItem,
    SignalSet,
    TrustHints,
)
from social_research_probe.platforms.registry import register
from social_research_probe.types import AdapterConfig


@register
class TikTokAdapter(PlatformAdapter):
    name: ClassVar[str] = "tiktok"
    default_limits: ClassVar[FetchLimits] = FetchLimits(max_items=30, recency_days=30)

    def __init__(self, config: AdapterConfig) -> None:
        self.config = config

    def health_check(self) -> bool:
        # Return True iff your API key / auth is available.
        return bool(self.config.get("data_dir"))

    def search(self, topic: str, limits: FetchLimits) -> list[RawItem]:
        # Call your platform API; return a list of RawItem objects.
        # See RawItem fields in social_research_probe/platforms/base.py.
        return []

    async def enrich(self, items: list[RawItem]) -> list[RawItem]:
        # Optional: hydrate with view/like/comment counts if not already present.
        return items

    def to_signals(self, items: list[RawItem]) -> list[SignalSet]:
        now = datetime.now(UTC)
        signals: list[SignalSet] = []
        for it in items:
            age_days = max(1, (now - it.published_at).days)
            views = int(it.metrics.get("views") or 0)
            likes = int(it.metrics.get("likes") or 0)
            comments = int(it.metrics.get("comments") or 0)
            signals.append(
                SignalSet(
                    views=views,
                    likes=likes,
                    comments=comments,
                    upload_date=it.published_at,
                    view_velocity=views / age_days,
                    engagement_ratio=(likes + comments) / max(1, views),
                    comment_velocity=comments / age_days,
                    cross_channel_repetition=0.0,
                    raw={},
                )
            )
        return signals

    def trust_hints(self, item: RawItem) -> TrustHints:
        return TrustHints(
            account_age_days=None,
            verified=None,
            subscriber_count=None,
            upload_cadence_days=None,
            citation_markers=[],
        )

    def url_normalize(self, url: str) -> str:
        return url.rstrip("/")
```

### Step 4 — Add a config section

Edit the canonical [`config.toml.example`](../config.toml.example):

```toml
[platforms.tiktok]
recency_days = 30
max_items = 30
enrich_top_n = 5
```

Any keys you add here become available inside your adapter via `self.config.get("your_key")`. Users override them with:

```bash
srp config set platforms.tiktok.max_items 100
```

### Step 5 — Add a secret (if the API needs a key)

The secret store is shared across all platforms. Follow the pattern from [`platforms/youtube/adapter.py`](../social_research_probe/platforms/youtube/adapter.py)'s `_api_key` method:

```python
def _api_key(self) -> str:
    import os

    key = os.environ.get("SRP_TIKTOK_API_KEY")
    if key:
        return key
    data_dir = self.config.get("data_dir")
    if data_dir is not None:
        from social_research_probe.commands.config import read_secret
        val = read_secret(data_dir, "tiktok_api_key")
        if val:
            return val
    from social_research_probe.errors import AdapterError
    raise AdapterError(
        "tiktok_api_key missing — run `srp config set-secret tiktok_api_key`"
    )
```

Users then run:
```bash
srp config set-secret tiktok_api_key
```
The secret is written to `~/.social-research-probe/secrets.toml` with `0600` permissions.

### Step 6 — Register a test fake

Follow the pattern in [`tests/fixtures/fake_youtube.py`](../tests/fixtures/fake_youtube.py). Create `tests/fixtures/fake_tiktok.py` with a `FakeTikTokAdapter` that returns deterministic items with no network calls. Opt in via env var:

```python
if os.environ.get("SRP_TEST_USE_FAKE_TIKTOK"):
    @register
    class FakeTikTokAdapter(PlatformAdapter):
        name = "tiktok"
        ...
```

Add `SRP_TEST_USE_FAKE_TIKTOK=1` to the test environments that exercise your adapter. This keeps integration tests offline and deterministic.

### Step 7 — Write tests

TDD workflow:

1. **Unit tests** (`tests/unit/test_tiktok_adapter.py`) — exercise `search`, `enrich`, `to_signals`, `trust_hints`, `url_normalize`, and `health_check` independently with mocked HTTP via `respx`.
2. **Pipeline integration test** (`tests/integration/test_research_tiktok.py`) — run `run_research` end-to-end with `SRP_TEST_USE_FAKE_TIKTOK=1` and assert the packet schema is produced.
3. **Contract test** — the existing `tests/contract/test_registry_contract.py` already asserts every registered platform implements the full adapter interface; your adapter is checked automatically.

Coverage gate is 100 % branch coverage — every branch of every method you write must be exercised by a test.

### Step 8 — Run it

```bash
srp research tiktok "AI safety" "latest-news"
srp config set platforms.tiktok.max_items 50
```

---

## What you don't have to do

Once the adapter returns `RawItem` and `SignalSet` objects, the rest of the pipeline is fully generic:

- **Scoring** — the trust/trend/opportunity formulas in [`scoring/`](../social_research_probe/scoring/) run against `SignalSet` directly.
- **Statistics** — all 20 statistical models in [`stats/`](../social_research_probe/stats/) work on any numeric feature set; no platform-specific code needed.
- **Charts** — the 10 chart renderers in [`viz/`](../social_research_probe/viz/) consume score-and-feature data, not platform data.
- **Corroboration** — claim extraction runs on `item.text_excerpt` plus your optional `fetch_text_for_claim_extraction` override.
- **Report generation** — the HTML/Markdown renderers (`render/`, `synthesize/`) consume the packet and do not look at the platform name.

You only own fetching and normalisation. Everything downstream is already platform-agnostic.

---

## Common pitfalls

| Pitfall | Fix |
|---|---|
| Forgot `@register` decorator | The adapter loads but `srp research tiktok …` raises `unknown platform`. |
| `name` class var empty or missing | `register` raises `ValueError`. |
| `published_at` not timezone-aware | Score age computations produce NaT. Always construct with `datetime(..., tzinfo=UTC)`. |
| Metrics stored as strings | `to_signals` gets division errors. Coerce to `int` inside `enrich`. |
| Blocking HTTP calls in `async enrich` | Wrap sync clients with `asyncio.to_thread(...)` (YouTube does this) or switch to `httpx.AsyncClient`. |
| Forgot to update `platforms/__init__.py` | Adapter is never imported, so `@register` never runs. |
| Config key missing from `config.toml.example` | `srp config set platforms.tiktok.max_items` works, but users have no discoverable reference. |

---

## Reference implementation

Every method above is demonstrated in [`social_research_probe/platforms/youtube/adapter.py`](../social_research_probe/platforms/youtube/adapter.py). Read it top-to-bottom before writing your own — it handles duration parsing, shorts filtering, concurrent hydration via `asyncio.to_thread` + `asyncio.gather`, and graceful error paths. Your adapter does not need to be as complete as YouTube's, but that file is the canonical blueprint.

---

## See also

- [How It Works](how-it-works.md) — the pipeline stages your adapter plugs into
- [Design Patterns](design-patterns.md) — the Adapter and Registry patterns explained
- [Testing](testing.md) — the test tiers your adapter must satisfy
- [Architecture](architecture.md) — system-wide view including where your adapter sits
