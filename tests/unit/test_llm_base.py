"""Tests for the LLMRunner abstract base class.

Verifies that LLMRunner cannot be instantiated directly and that a concrete
subclass implementing both abstract methods works correctly.

Who calls it: pytest, run as part of the unit test suite.
"""

from __future__ import annotations

import pytest

from social_research_probe.llm.base import LLMRunner


class _ConcreteRunner(LLMRunner):
    """Minimal concrete LLMRunner used only in tests."""

    name = "test_concrete"

    def health_check(self) -> bool:
        """Always returns True for testing."""
        return True

    def run(self, prompt: str, *, schema: dict | None = None) -> dict:
        """Echo prompt back as a dict for testing."""
        return {"echo": prompt}


def test_llm_runner_is_abstract() -> None:
    """LLMRunner cannot be instantiated directly because it is abstract.

    Attempting to do so must raise TypeError — Python enforces this for any
    class that has unimplemented abstract methods.
    """
    with pytest.raises(TypeError):
        LLMRunner()


def test_concrete_subclass_works() -> None:
    """A concrete subclass that implements both abstract methods can be used.

    Verifies that instantiation succeeds and that health_check() and run()
    return the values defined by the concrete implementation.
    """
    runner = _ConcreteRunner()
    assert runner.health_check() is True
    result = runner.run("hello world")
    assert result == {"echo": "hello world"}
