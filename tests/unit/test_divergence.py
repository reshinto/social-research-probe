"""Tests for the deterministic Jaccard divergence helper."""

from __future__ import annotations

from social_research_probe.synthesize.divergence import jaccard_divergence


def test_identical_strings_zero_divergence():
    assert jaccard_divergence("the sky is blue", "the sky is blue") == 0.0


def test_disjoint_strings_full_divergence():
    assert jaccard_divergence("apple orange", "car truck") == 1.0


def test_both_empty_returns_zero():
    assert jaccard_divergence("", "") == 0.0


def test_one_empty_returns_one():
    assert jaccard_divergence("hello world", "") == 1.0
    assert jaccard_divergence("", "hello world") == 1.0


def test_case_insensitive():
    assert jaccard_divergence("Hello World", "hello world") == 0.0


def test_punctuation_normalised():
    assert jaccard_divergence("hello, world!", "hello world") == 0.0


def test_partial_overlap_known_value():
    # token sets {a,b,c,d} vs {c,d,e,f} → intersection 2, union 6 → 1 - 2/6 = 0.6666…
    result = jaccard_divergence("a b c d", "c d e f")
    assert abs(result - (2 / 3)) < 1e-9
