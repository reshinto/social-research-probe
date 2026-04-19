"""Tests for the LLM runner registry (llm/registry.py).

Covers register(), get_runner(), and list_runners(). Each test restores the
registry to its pre-test state via a fixture so tests are fully isolated from
each other and from the real runners registered at import time.

Who calls it: pytest, run as part of the unit test suite.
"""
from __future__ import annotations

import pytest

import social_research_probe.llm.registry as registry_module
from social_research_probe.errors import ValidationError
from social_research_probe.llm.base import LLMRunner
from social_research_probe.llm.registry import get_runner, list_runners, register


@pytest.fixture(autouse=True)
def _isolated_registry():
    """Save and restore _REGISTRY around every test.

    Why: _REGISTRY is module-level state. Without isolation, a runner registered
    in one test leaks into subsequent tests, causing false positives or failures.
    """
    original = dict(registry_module._REGISTRY)
    yield
    # Restore the registry to exactly the state it was in before the test ran.
    registry_module._REGISTRY.clear()
    registry_module._REGISTRY.update(original)


class _FakeRunner(LLMRunner):
    """Minimal LLMRunner for registry tests."""

    name = "fake"

    def health_check(self) -> bool:
        """Always available in tests."""
        return True

    def run(self, prompt: str, *, schema: dict | None = None) -> dict:
        """Returns a fixed dict."""
        return {"fake": True}


def test_register_and_get_runner() -> None:
    """Registering a runner class and then calling get_runner returns an instance.

    Verifies the full round-trip: @register stores the class, get_runner()
    instantiates it and returns the correct type.
    """
    register(_FakeRunner)
    instance = get_runner("fake")
    assert isinstance(instance, _FakeRunner)


def test_get_unknown_raises_validation_error() -> None:
    """get_runner raises ValidationError for a name not in the registry.

    Why ValidationError: unknown names are a user/config error (exit code 2),
    not an adapter failure.
    """
    with pytest.raises(ValidationError, match="unknown LLM runner"):
        get_runner("nonexistent_runner_xyz")


def test_list_runners_sorted() -> None:
    """list_runners returns a sorted list of registered runner names.

    Registers two runners out of alphabetical order and asserts the result
    is sorted ascending.
    """

    class _AlphaRunner(LLMRunner):
        name = "alpha"

        def health_check(self) -> bool:
            return True

        def run(self, prompt: str, *, schema: dict | None = None) -> dict:
            return {}

    class _ZetaRunner(LLMRunner):
        name = "zeta"

        def health_check(self) -> bool:
            return True

        def run(self, prompt: str, *, schema: dict | None = None) -> dict:
            return {}

    # Register in reverse alphabetical order to confirm sorting is applied.
    register(_ZetaRunner)
    register(_AlphaRunner)

    names = list_runners()
    # Extract only the names we just registered to avoid coupling to real runners.
    subset = [n for n in names if n in {"alpha", "zeta"}]
    assert subset == ["alpha", "zeta"]
    # Confirm the full list is also sorted.
    assert names == sorted(names)


def test_register_missing_name_raises_value_error() -> None:
    """register() raises ValueError when the class has no `name` attribute.

    Why: a nameless runner cannot be looked up, so registration must fail
    immediately rather than silently producing an unusable entry.
    """

    class _NoName(LLMRunner):
        # Deliberately omit the name class variable.
        def health_check(self) -> bool:
            return True

        def run(self, prompt: str, *, schema: dict | None = None) -> dict:
            return {}

    with pytest.raises(ValueError, match="must define class var `name`"):
        register(_NoName)
