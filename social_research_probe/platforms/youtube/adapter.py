"""Real YouTubeAdapter. In tests, `tests/fixtures/fake_youtube.py` pre-empts
this registration. In production, this module is imported and replaces the
fixture's registration."""
from __future__ import annotations

import os
from typing import Any, ClassVar

from social_research_probe.errors import AdapterError
from social_research_probe.platforms.base import (
    FetchLimits,
    PlatformAdapter,
    RawItem,
    SignalSet,
    TrustHints,
)
from social_research_probe.platforms.registry import register


@register
class YouTubeAdapter(PlatformAdapter):
    name: ClassVar[str] = "youtube"
    default_limits: ClassVar[FetchLimits] = FetchLimits(max_items=20, recency_days=90)

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config

    def _api_key(self) -> str:
        key = os.environ.get("SRP_YOUTUBE_API_KEY")
        if key:
            return key
        data_dir = self.config.get("data_dir")
        if data_dir is not None:
            from social_research_probe.commands.config import read_secret
            val = read_secret(data_dir, "youtube_api_key")
            if val:
                return val
        raise AdapterError(
            "youtube_api_key missing — run `srp config set-secret youtube_api_key` in a terminal"
        )

    def health_check(self) -> bool:
        self._api_key()
        return True

    def search(self, topic: str, limits: FetchLimits) -> list[RawItem]:  # pragma: no cover — live
        from social_research_probe.platforms.youtube import fetch
        client = fetch.build_client(self._api_key())
        items = fetch.search_videos(client, topic=topic, max_items=limits.max_items, published_after=None)
        return self._stub_items_from_search(items)

    def _stub_items_from_search(self, raw: list[dict]) -> list[RawItem]:  # pragma: no cover
        raise NotImplementedError("populated in P7 live smoke test; tests use FakeYouTubeAdapter")

    def enrich(self, items: list[RawItem]) -> list[RawItem]:  # pragma: no cover
        return items

    def to_signals(self, items: list[RawItem]) -> list[SignalSet]:  # pragma: no cover
        return []

    def trust_hints(self, item: RawItem) -> TrustHints:  # pragma: no cover
        return TrustHints(None, None, None, None, [])

    def url_normalize(self, url: str) -> str:
        from urllib.parse import parse_qs, urlparse, urlunparse
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        keep = {"v": qs["v"]} if "v" in qs else {}
        query = "&".join(f"{k}={v[0]}" for k, v in keep.items())
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", query, ""))
