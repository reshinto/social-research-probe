"""Platform registry: @register, get_client, unknown platform raises."""

from __future__ import annotations

import pytest

from social_research_probe.platforms.base import FetchLimits, RawItem, SearchClient
from social_research_probe.platforms.registry import get_client, list_clients, register
from social_research_probe.utils.core.errors import ValidationError
from social_research_probe.utils.core.types import AdapterConfig


def test_register_and_get():
    @register
    class ToyClient(SearchClient):
        name = "toy-registry-test"
        default_limits = FetchLimits()

        def __init__(self, config: AdapterConfig) -> None:
            self.config = config

        def health_check(self) -> bool:
            return True

        def find_by_topic(self, topic: str, limits: FetchLimits) -> list[RawItem]:
            return []

        async def fetch_item_details(self, items: list[RawItem]) -> list[RawItem]:
            return items

    client = get_client("toy-registry-test", {"k": "v"})
    assert isinstance(client, ToyClient)
    assert client.config == {"k": "v"}
    assert "toy-registry-test" in list_clients()


def test_unknown_platform_raises():
    with pytest.raises(ValidationError) as excinfo:
        get_client("nonexistent", {})
    assert "nonexistent" in str(excinfo.value)


def test_register_class_without_name_raises():
    with pytest.raises(ValueError, match="must define class var `name`"):

        @register
        class NoNameClient(SearchClient):
            default_limits = FetchLimits()

            def __init__(self, config: AdapterConfig):
                self.config = config

            def health_check(self):
                return True

            def find_by_topic(self, topic, limits):
                return []

            async def fetch_item_details(self, items):
                return items
