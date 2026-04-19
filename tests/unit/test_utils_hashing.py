"""
Tests for ``social_research_probe.utils.hashing``.

Verifies that ``stable_hash`` produces canonical, deterministic SHA-256 hex
digests for JSON-serialisable objects, regardless of dict key-insertion order,
and that the output format is correct (64-character lowercase hex string).
"""

from __future__ import annotations

import pytest

from social_research_probe.utils.hashing import stable_hash


def test_stable_hash_dict_canonical() -> None:
    """Same dict with different key-insertion order must produce the same hash."""
    dict_a = {"b": 2, "a": 1}
    dict_b = {"a": 1, "b": 2}
    assert stable_hash(dict_a) == stable_hash(dict_b)


def test_stable_hash_different_values() -> None:
    """Dicts with different values must produce different hashes."""
    assert stable_hash({"x": 1}) != stable_hash({"x": 2})


def test_stable_hash_string() -> None:
    """A plain string input must be hashed without error."""
    result = stable_hash("hello world")
    assert isinstance(result, str)
    assert len(result) == 64


def test_stable_hash_returns_hex_string() -> None:
    """Result must be a 64-character lowercase hexadecimal string."""
    result = stable_hash({"key": "value", "number": 42, "flag": True})
    assert len(result) == 64
    # Every character must be a valid hex digit.
    assert all(c in "0123456789abcdef" for c in result)
