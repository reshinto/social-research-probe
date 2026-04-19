"""Platform registry: @register, get_adapter, unknown platform raises."""
from __future__ import annotations

from typing import Any

import pytest

from social_research_probe.errors import ValidationError
from social_research_probe.platforms.base import (
    FetchLimits,
    PlatformAdapter,
    RawItem,
    SignalSet,
    TrustHints,
)
from social_research_probe.platforms.registry import get_adapter, list_adapters, register


def test_register_and_get():
    @register
    class ToyAdapter(PlatformAdapter):
        name = "toy-registry-test"
        default_limits = FetchLimits()

        def __init__(self, config: dict[str, Any]) -> None:
            self.config = config

        def health_check(self) -> bool: return True
        def search(self, topic: str, limits: FetchLimits) -> list[RawItem]: return []
        def enrich(self, items: list[RawItem]) -> list[RawItem]: return items
        def to_signals(self, items: list[RawItem]) -> list[SignalSet]: return []
        def trust_hints(self, item: RawItem) -> TrustHints:
            return TrustHints(None, None, None, None, [])
        def url_normalize(self, url: str) -> str: return url

    adapter = get_adapter("toy-registry-test", {"k": "v"})
    assert isinstance(adapter, ToyAdapter)
    assert adapter.config == {"k": "v"}
    assert "toy-registry-test" in list_adapters()


def test_unknown_platform_raises():
    with pytest.raises(ValidationError) as excinfo:
        get_adapter("nonexistent", {})
    assert "nonexistent" in str(excinfo.value)


def test_register_class_without_name_raises():
    """Line 14: @register on a class with no 'name' raises ValueError."""
    with pytest.raises(ValueError, match="must define class var `name`"):
        @register
        class NoNameAdapter(PlatformAdapter):
            # deliberately no 'name' class var
            default_limits = FetchLimits()

            def __init__(self, config): pass
            def health_check(self): return True  # noqa: E704
            def search(self, topic, limits): return []  # noqa: E704
            def enrich(self, items): return items  # noqa: E704
            def to_signals(self, items): return []  # noqa: E704
            def trust_hints(self, item): return TrustHints(None, None, None, None, [])  # noqa: E704
            def url_normalize(self, url): return url  # noqa: E704
