"""YouTubeConnector must satisfy PlatformClient/PlatformMapper ABCs + raise AdapterError when
API key is missing."""

from __future__ import annotations

import pytest
from social_research_probe.utils.core.errors import AdapterError


def test_adapter_requires_api_key(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("SRP_YOUTUBE_API_KEY", raising=False)
    from social_research_probe.services.sourcing.youtube import YouTubeConnector

    adapter = YouTubeConnector({"data_dir": None})
    with pytest.raises(AdapterError):
        adapter.health_check()



def test_api_key_from_env(monkeypatch: pytest.MonkeyPatch):
    """YouTubeAPI._api_key returns env var when SRP_YOUTUBE_API_KEY is set."""
    monkeypatch.setenv("SRP_YOUTUBE_API_KEY", "test-api-key-from-env")
    from social_research_probe.technologies.media_fetch.youtube_api import resolve_youtube_api_key

    assert resolve_youtube_api_key() == "test-api-key-from-env"


def test_api_key_from_data_dir(monkeypatch: pytest.MonkeyPatch, tmp_data_dir):
    """YouTubeAPI._api_key reads from secrets file via read_secret."""
    monkeypatch.delenv("SRP_YOUTUBE_API_KEY", raising=False)
    from social_research_probe.commands.config import write_secret
    from social_research_probe.technologies.media_fetch.youtube_api import resolve_youtube_api_key

    write_secret("youtube_api_key", "key-from-file")
    assert resolve_youtube_api_key() == "key-from-file"


def test_health_check_returns_true(monkeypatch: pytest.MonkeyPatch):
    """Line 45: health_check returns True when API key is available."""
    monkeypatch.setenv("SRP_YOUTUBE_API_KEY", "some-key")
    from social_research_probe.services.sourcing.youtube import YouTubeConnector

    adapter = YouTubeConnector({"data_dir": None})
    assert adapter.health_check() is True


def test_parse_duration_no_match_returns_zero():
    """Line 51: _parse_duration_seconds returns 0 when duration doesn't match PT pattern."""
    from social_research_probe.utils.core.coerce import parse_duration_seconds as _parse_duration_seconds

    assert _parse_duration_seconds("invalid") == 0


def test_parse_duration_hours_minutes_seconds():
    """Lines 52-53: _parse_duration_seconds computes h*3600+m*60+s."""
    from social_research_probe.utils.core.coerce import parse_duration_seconds as _parse_duration_seconds

    assert _parse_duration_seconds("PT1H30M45S") == 1 * 3600 + 30 * 60 + 45


def test_parse_duration_minutes_only():
    """Lines 52-53: _parse_duration_seconds handles minutes-only format."""
    from social_research_probe.utils.core.coerce import parse_duration_seconds as _parse_duration_seconds

    assert _parse_duration_seconds("PT5M") == 300


def test_api_key_raises_when_both_absent(monkeypatch: pytest.MonkeyPatch):
    """YouTubeAPI._api_key raises AdapterError when no env var and no data_dir secret."""
    monkeypatch.delenv("SRP_YOUTUBE_API_KEY", raising=False)
    from social_research_probe.technologies.media_fetch.youtube_api import resolve_youtube_api_key

    with pytest.raises(AdapterError):
        resolve_youtube_api_key()


def test_api_key_data_dir_set_but_no_secret_raises(monkeypatch: pytest.MonkeyPatch, tmp_data_dir):
    """YouTubeAPI._api_key raises AdapterError when no secret exists in data dir."""
    monkeypatch.delenv("SRP_YOUTUBE_API_KEY", raising=False)
    from social_research_probe.technologies.media_fetch.youtube_api import resolve_youtube_api_key

    with pytest.raises(AdapterError):
        resolve_youtube_api_key()
