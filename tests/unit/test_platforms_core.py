"""Tests for platforms.{base, registry, state, __init__}."""

from __future__ import annotations

import pytest

from social_research_probe.platforms import base, registry
from social_research_probe.platforms.state import PipelineState
from social_research_probe.utils.core.errors import ValidationError


class TestRegistry:
    def test_register_requires_name(self):
        class Bad:
            name = ""

        with pytest.raises(ValueError):
            registry.register(Bad)  # type: ignore[arg-type]

    def test_get_unknown(self):
        with pytest.raises(ValidationError):
            registry.get_client("missing-pkg-xyz", {})

    def test_get_meta_all_raises(self):
        with pytest.raises(ValidationError):
            registry.get_client("all", {})

    def test_list_clients_excludes_all(self):
        assert "all" not in registry.list_clients()

    def test_register_and_get_roundtrip(self, monkeypatch):
        class FakeClient(base.PlatformClient):
            name = "fake-test-platform"

            def __init__(self, config):
                self.config = config

            def health_check(self) -> bool:
                return True

        monkeypatch.setitem(registry.CLIENTS, "fake-test-platform", None)
        registry.register(FakeClient)
        assert "fake-test-platform" in registry.list_clients()
        out = registry.get_client("fake-test-platform", {"k": 1})
        assert isinstance(out, FakeClient)
        assert out.config == {"k": 1}
        registry.CLIENTS.pop("fake-test-platform", None)


class TestPipelineState:
    def test_set_get_stage(self):
        s = PipelineState(platform_type="x", cmd=None, cache=None)
        s.set_stage_output("fetch", {"items": [1]})
        assert s.get_stage_output("fetch") == {"items": [1]}

    def test_get_stage_default(self):
        s = PipelineState(platform_type="x", cmd=None, cache=None)
        assert s.get_stage_output("missing") == {}

    def test_set_get_service(self):
        s = PipelineState(platform_type="x", cmd=None, cache=None)
        s.set_service_output("svc", {"service": "svc", "data": 1})
        assert s.get_service_output("svc") == {"service": "svc", "data": 1}

    def test_get_service_default(self):
        s = PipelineState(platform_type="x", cmd=None, cache=None)
        assert s.get_service_output("missing") is None

    def test_set_service_replaces(self):
        s = PipelineState(platform_type="x", cmd=None, cache=None)
        s.set_service_output("svc", {"service": "svc", "v": 1})
        s.set_service_output("svc", {"service": "svc", "v": 2})
        assert s.get_service_output("svc")["v"] == 2


def test_base_classes_abstract():
    with pytest.raises(TypeError):
        base.PlatformClient()  # type: ignore[abstract]
    with pytest.raises(TypeError):
        base.SearchClient()  # type: ignore[abstract]
    with pytest.raises(TypeError):
        base.FetchClient()  # type: ignore[abstract]
    with pytest.raises(TypeError):
        base.BaseStage()  # type: ignore[abstract]
    with pytest.raises(TypeError):
        base.BaseResearchPlatform()  # type: ignore[abstract]


def test_fetch_limits_defaults():
    fl = base.FetchLimits()
    assert fl.max_items == 20
    assert fl.recency_days == 90


def test_pipelines_module_exports():
    from social_research_probe import platforms

    pipelines = platforms.PIPELINES
    assert "youtube" in pipelines
    assert "all" in pipelines


def test_pipelines_module_unknown_attr():
    from social_research_probe import platforms

    with pytest.raises(AttributeError):
        _ = platforms.NOT_A_THING
