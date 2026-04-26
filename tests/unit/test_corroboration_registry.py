"""Tests for corroboration/registry.py — register, get_backend, list_backends.

What: Verifies decorator registration, look-up by name, unknown-name error, and
sorted listing.
Who calls it: pytest, as part of the unit test suite.
"""

from __future__ import annotations

import pytest
from social_research_probe.corroboration import registry as reg_module
from social_research_probe.corroboration.base import CorroborationBackend, CorroborationResult
from social_research_probe.errors import ValidationError


@pytest.fixture(autouse=True)
def clean_registry():
    """Save and restore the registry around each test to avoid cross-test pollution."""
    original = dict(reg_module._REGISTRY)
    yield
    reg_module._REGISTRY.clear()
    reg_module._REGISTRY.update(original)


def _make_backend(name_val: str) -> type[CorroborationBackend]:
    """Factory: create a minimal concrete CorroborationBackend subclass."""

    class _Stub(CorroborationBackend):
        name = name_val

        def health_check(self) -> bool:
            return True

        def corroborate(self, claim) -> CorroborationResult:
            return CorroborationResult(verdict="inconclusive", confidence=0.5, reasoning="stub")

    _Stub.__name__ = f"Stub_{name_val}"
    return _Stub


def test_register_and_get_backend():
    """@register adds the backend to the registry and get_backend returns an instance."""
    stub_cls = reg_module.register(_make_backend("test_backend_a"))
    backend = reg_module.get_backend("test_backend_a")
    assert isinstance(backend, stub_cls)


def test_get_unknown_raises_validation_error():
    """get_backend raises ValidationError for an unrecognised backend name."""
    with pytest.raises(ValidationError, match="unknown corroboration backend"):
        reg_module.get_backend("__definitely_not_registered__")


def test_list_backends_sorted():
    """list_backends returns sorted backend names including newly registered ones."""
    reg_module.register(_make_backend("zebra"))
    reg_module.register(_make_backend("alpha"))
    names = reg_module.list_backends()
    # The result must be sorted.
    assert names == sorted(names)
    # Our two test backends must appear.
    assert "zebra" in names
    assert "alpha" in names
    # 'alpha' must come before 'zebra' in sorted order.
    assert names.index("alpha") < names.index("zebra")


def test_register_class_without_name_raises():
    """Line 37: @register on class without 'name' raises ValueError."""

    class NoName(CorroborationBackend):
        def health_check(self) -> bool:
            return True

        def corroborate(self, claim) -> CorroborationResult:
            return CorroborationResult(verdict="inconclusive", confidence=0.0, reasoning="")

    with pytest.raises(ValueError, match="must define class var `name`"):
        reg_module.register(NoName)


def test_builtin_backends_are_registered_on_package_import():
    """The package import side effect should register the built-in backends."""
    names = reg_module.list_backends()
    assert {"brave", "exa", "llm_search", "tavily"} <= set(names)


def test_get_backend_rejects_unknown_backend_name():
    """Only registered backend names are accepted by the registry."""
    with pytest.raises(ValidationError, match="unknown corroboration backend"):
        reg_module.get_backend("__retired_backend__")
