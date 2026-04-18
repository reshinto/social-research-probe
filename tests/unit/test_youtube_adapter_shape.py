"""YouTube adapter must satisfy PlatformAdapter ABC + raise AdapterError when
API key is missing."""
from __future__ import annotations

import pytest

from social_research_probe.errors import AdapterError


def test_adapter_requires_api_key(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("SRP_YOUTUBE_API_KEY", raising=False)
    from social_research_probe.platforms.youtube.adapter import YouTubeAdapter

    adapter = YouTubeAdapter({"data_dir": None})
    with pytest.raises(AdapterError):
        adapter.health_check()


def test_url_normalize_strips_extra_params():
    from social_research_probe.platforms.youtube.adapter import YouTubeAdapter

    adapter = YouTubeAdapter({"data_dir": None})
    url = "https://www.youtube.com/watch?v=abc123&t=30s&ab_channel=X"
    assert "v=abc123" in adapter.url_normalize(url)
    assert "ab_channel" not in adapter.url_normalize(url)
