"""Tests for corroboration/exa.py, brave.py, and tavily.py backends.

What: Verifies health_check env-var logic, _api_key error handling, and
_build_result result construction for each of the three HTTP search backends
— all without making live network calls.
Who calls it: pytest, as part of the unit test suite.
"""

from __future__ import annotations

import pytest

from social_research_probe.corroboration.base import CorroborationResult
from social_research_probe.corroboration.brave import BraveBackend
from social_research_probe.corroboration.exa import ExaBackend
from social_research_probe.corroboration.tavily import TavilyBackend
from social_research_probe.errors import AdapterError


class _FakeClaim:
    """Minimal stand-in for a Claim dataclass."""

    def __init__(self, text: str = "Test claim.") -> None:
        self.text = text
        self.source_text = ""
        self.index = 0


# ---------------------------------------------------------------------------
# ExaBackend
# ---------------------------------------------------------------------------


def test_exa_health_check_true_when_key_set(monkeypatch):
    """ExaBackend.health_check() returns True when SRP_EXA_API_KEY is present."""
    monkeypatch.setenv("SRP_EXA_API_KEY", "fake-exa-key")
    assert ExaBackend().health_check() is True


def test_exa_health_check_false_when_key_missing(monkeypatch):
    """ExaBackend.health_check() returns False when SRP_EXA_API_KEY is absent."""
    monkeypatch.delenv("SRP_EXA_API_KEY", raising=False)
    assert ExaBackend().health_check() is False


def test_exa_api_key_raises_when_missing(monkeypatch):
    """ExaBackend._api_key() raises AdapterError when SRP_EXA_API_KEY is not set."""
    monkeypatch.delenv("SRP_EXA_API_KEY", raising=False)
    with pytest.raises(AdapterError, match="SRP_EXA_API_KEY"):
        ExaBackend()._api_key()


def test_exa_build_result_with_results():
    """_build_result returns verdict='supported' and sources when URLs are present."""
    backend = ExaBackend()
    claim = _FakeClaim()
    raw = [{"url": "https://example.com/a"}, {"url": "https://example.com/b"}]
    result = backend._build_result(claim, raw)
    assert isinstance(result, CorroborationResult)
    assert result.verdict == "supported"
    assert result.backend_name == "exa"
    assert "https://example.com/a" in result.sources
    assert "https://example.com/b" in result.sources
    assert result.confidence > 0.0


def test_exa_build_result_empty_results():
    """_build_result returns verdict='inconclusive' and zero confidence when no URLs found."""
    backend = ExaBackend()
    claim = _FakeClaim()
    result = backend._build_result(claim, [])
    assert result.verdict == "inconclusive"
    assert result.confidence == 0.0
    assert result.sources == []


# ---------------------------------------------------------------------------
# BraveBackend
# ---------------------------------------------------------------------------


def test_brave_health_check_true_when_key_set(monkeypatch):
    """BraveBackend.health_check() returns True when SRP_BRAVE_API_KEY is present."""
    monkeypatch.setenv("SRP_BRAVE_API_KEY", "fake-brave-key")
    assert BraveBackend().health_check() is True


def test_brave_health_check_false_when_key_missing(monkeypatch):
    """BraveBackend.health_check() returns False when SRP_BRAVE_API_KEY is absent."""
    monkeypatch.delenv("SRP_BRAVE_API_KEY", raising=False)
    assert BraveBackend().health_check() is False


def test_brave_api_key_raises_when_missing(monkeypatch):
    """BraveBackend._api_key() raises AdapterError when SRP_BRAVE_API_KEY is not set."""
    monkeypatch.delenv("SRP_BRAVE_API_KEY", raising=False)
    with pytest.raises(AdapterError, match="SRP_BRAVE_API_KEY"):
        BraveBackend()._api_key()


def test_brave_build_result_with_results():
    """_build_result returns verdict='supported' and sources when URLs are present."""
    backend = BraveBackend()
    claim = _FakeClaim()
    raw = [{"url": "https://brave-result.com/1"}, {"url": "https://brave-result.com/2"}]
    result = backend._build_result(claim, raw)
    assert result.verdict == "supported"
    assert result.backend_name == "brave"
    assert "https://brave-result.com/1" in result.sources
    assert result.confidence > 0.0


def test_brave_build_result_empty_results():
    """_build_result returns verdict='inconclusive' and zero confidence when no URLs found."""
    backend = BraveBackend()
    claim = _FakeClaim()
    result = backend._build_result(claim, [])
    assert result.verdict == "inconclusive"
    assert result.confidence == 0.0
    assert result.sources == []


# ---------------------------------------------------------------------------
# TavilyBackend
# ---------------------------------------------------------------------------


def test_tavily_health_check_true_when_key_set(monkeypatch):
    """TavilyBackend.health_check() returns True when SRP_TAVILY_API_KEY is present."""
    monkeypatch.setenv("SRP_TAVILY_API_KEY", "fake-tavily-key")
    assert TavilyBackend().health_check() is True


def test_tavily_health_check_false_when_key_missing(monkeypatch):
    """TavilyBackend.health_check() returns False when SRP_TAVILY_API_KEY is absent."""
    monkeypatch.delenv("SRP_TAVILY_API_KEY", raising=False)
    assert TavilyBackend().health_check() is False


def test_tavily_api_key_raises_when_missing(monkeypatch):
    """TavilyBackend._api_key() raises AdapterError when SRP_TAVILY_API_KEY is not set."""
    monkeypatch.delenv("SRP_TAVILY_API_KEY", raising=False)
    with pytest.raises(AdapterError, match="SRP_TAVILY_API_KEY"):
        TavilyBackend()._api_key()


def test_tavily_build_result_with_results():
    """_build_result returns verdict='supported' and sources when URLs are present."""
    backend = TavilyBackend()
    claim = _FakeClaim()
    raw = [
        {"url": "https://tavily-result.com/a"},
        {"url": "https://tavily-result.com/b"},
        {"url": "https://tavily-result.com/c"},
    ]
    result = backend._build_result(claim, raw)
    assert result.verdict == "supported"
    assert result.backend_name == "tavily"
    assert len(result.sources) == 3
    # 3 sources * 0.2 = 0.6 confidence
    assert abs(result.confidence - 0.6) < 1e-9


def test_tavily_build_result_empty_results():
    """_build_result returns verdict='inconclusive' and zero confidence when no URLs found."""
    backend = TavilyBackend()
    claim = _FakeClaim()
    result = backend._build_result(claim, [])
    assert result.verdict == "inconclusive"
    assert result.confidence == 0.0
    assert result.sources == []


def test_brave_api_key_returns_key_when_set(monkeypatch):
    """Line 61: _api_key() returns the key string when the env var is set."""
    from social_research_probe.corroboration.brave import BraveBackend

    monkeypatch.setenv("SRP_BRAVE_API_KEY", "test-brave-key")
    assert BraveBackend()._api_key() == "test-brave-key"


def test_exa_api_key_returns_key_when_set(monkeypatch):
    """Line 62: _api_key() returns the key string when the env var is set."""
    from social_research_probe.corroboration.exa import ExaBackend

    monkeypatch.setenv("SRP_EXA_API_KEY", "test-exa-key")
    assert ExaBackend()._api_key() == "test-exa-key"


def test_tavily_api_key_returns_key_when_set(monkeypatch):
    """Line 62: _api_key() returns the key string when the env var is set."""
    from social_research_probe.corroboration.tavily import TavilyBackend

    monkeypatch.setenv("SRP_TAVILY_API_KEY", "test-tavily-key")
    assert TavilyBackend()._api_key() == "test-tavily-key"


# ---------------------------------------------------------------------------
# _search() — monkeypatched urllib.request.urlopen
# ---------------------------------------------------------------------------


def _make_fake_urlopen(response_body: bytes):
    """Return a fake urlopen context-manager that yields the given bytes."""

    class _FakeResp:
        def read(self):
            return response_body

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

    return lambda req, timeout=15: _FakeResp()


def test_exa_search_returns_results(monkeypatch):
    """_search() parses the 'results' list from the Exa API JSON response."""
    import json
    import urllib.request

    monkeypatch.setenv("SRP_EXA_API_KEY", "k")
    body = json.dumps({"results": [{"url": "https://a.com"}, {"url": "https://b.com"}]}).encode()
    monkeypatch.setattr(urllib.request, "urlopen", _make_fake_urlopen(body))
    results = ExaBackend()._search("test query")
    assert len(results) == 2
    assert results[0]["url"] == "https://a.com"


def test_exa_corroborate_end_to_end(monkeypatch):
    """corroborate() wires _search() to _build_result() and returns a CorroborationResult."""
    import json
    import urllib.request

    monkeypatch.setenv("SRP_EXA_API_KEY", "k")
    body = json.dumps({"results": [{"url": "https://example.com"}]}).encode()
    monkeypatch.setattr(urllib.request, "urlopen", _make_fake_urlopen(body))
    result = ExaBackend().corroborate(_FakeClaim("some claim"))
    assert result.verdict == "supported"
    assert "https://example.com" in result.sources


def test_brave_search_returns_results(monkeypatch):
    """_search() parses web.results from the Brave API JSON response."""
    import json
    import urllib.request

    monkeypatch.setenv("SRP_BRAVE_API_KEY", "k")
    body = json.dumps({"web": {"results": [{"url": "https://brave.com"}]}}).encode()
    monkeypatch.setattr(urllib.request, "urlopen", _make_fake_urlopen(body))
    results = BraveBackend()._search("test query")
    assert results == [{"url": "https://brave.com"}]


def test_brave_corroborate_end_to_end(monkeypatch):
    """corroborate() wires _search() to _build_result() and returns a CorroborationResult."""
    import json
    import urllib.request

    monkeypatch.setenv("SRP_BRAVE_API_KEY", "k")
    body = json.dumps({"web": {"results": [{"url": "https://brave.com"}]}}).encode()
    monkeypatch.setattr(urllib.request, "urlopen", _make_fake_urlopen(body))
    result = BraveBackend().corroborate(_FakeClaim("some claim"))
    assert result.verdict == "supported"
    assert "https://brave.com" in result.sources


def test_tavily_search_returns_results(monkeypatch):
    """_search() parses the 'results' list from the Tavily API JSON response."""
    import json
    import urllib.request

    monkeypatch.setenv("SRP_TAVILY_API_KEY", "k")
    body = json.dumps({"results": [{"url": "https://tavily.com"}]}).encode()
    monkeypatch.setattr(urllib.request, "urlopen", _make_fake_urlopen(body))
    results = TavilyBackend()._search("test query")
    assert results == [{"url": "https://tavily.com"}]


def test_tavily_corroborate_end_to_end(monkeypatch):
    """corroborate() wires _search() to _build_result() and returns a CorroborationResult."""
    import json
    import urllib.request

    monkeypatch.setenv("SRP_TAVILY_API_KEY", "k")
    body = json.dumps({"results": [{"url": "https://tavily.com"}]}).encode()
    monkeypatch.setattr(urllib.request, "urlopen", _make_fake_urlopen(body))
    result = TavilyBackend().corroborate(_FakeClaim("some claim"))
    assert result.verdict == "supported"
    assert "https://tavily.com" in result.sources
