"""Tests for misc utils: search.query, purposes.merge, cli.parsing, display."""

from __future__ import annotations

import pytest

from social_research_probe.utils.cli.parsing import _id_selector
from social_research_probe.utils.core.errors import ValidationError
from social_research_probe.utils.display.cli_output import emit
from social_research_probe.utils.display.fast_mode import (
    FAST_MODE_MAX_PROVIDERS,
    FAST_MODE_TOP_N,
    fast_mode_enabled,
)
from social_research_probe.utils.purposes.merge import MergedPurpose, merge_purposes
from social_research_probe.utils.search.query import enrich_query


class TestEnrichQuery:
    def test_passes_through_when_no_keywords(self):
        assert enrich_query("ai", "the") == "ai"

    def test_appends_meaningful_keywords(self):
        out = enrich_query("rust", "performance benchmarks")
        assert "performance" in out
        assert "benchmarks" in out
        assert out.startswith("rust ")

    def test_caps_at_three(self):
        out = enrich_query("topic", "alpha beta gamma delta epsilon")
        words = out.split()[1:]
        assert len(words) == 3

    def test_dedupes(self):
        out = enrich_query("topic", "alpha alpha beta")
        words = out.split()[1:]
        assert words.count("alpha") == 1


class TestMergePurposes:
    def test_unknown_raises(self):
        with pytest.raises(ValidationError, match="unknown"):
            merge_purposes({}, ["nope"])

    def test_missing_method_raises(self):
        purposes = {"x": {"method": None, "evidence_priorities": []}}
        with pytest.raises(ValidationError, match="missing required key 'method'"):
            merge_purposes(purposes, ["x"])

    def test_combines_methods_dedupe(self):
        purposes = {
            "a": {"method": "M1", "evidence_priorities": ["p1"]},
            "b": {"method": "M1", "evidence_priorities": ["p2"]},
        }
        merged = merge_purposes(purposes, ["a", "b"])
        assert merged.method == "M1"
        assert merged.evidence_priorities == ("p1", "p2")
        assert merged.names == ("a", "b")
        assert isinstance(merged, MergedPurpose)

    def test_scoring_overrides_max_wins(self):
        purposes = {
            "a": {"method": "x", "evidence_priorities": [], "scoring_overrides": {"k": 0.5}},
            "b": {"method": "y", "evidence_priorities": [], "scoring_overrides": {"k": 0.9}},
        }
        merged = merge_purposes(purposes, ["a", "b"])
        assert merged.scoring_overrides["k"] == 0.9


class TestIdSelector:
    def test_empty_returns_empty_list(self):
        assert _id_selector("") == []

    def test_all_keyword(self):
        assert _id_selector("all") == "all"

    def test_csv(self):
        assert _id_selector("1, 2, 3") == [1, 2, 3]

    def test_invalid_raises(self):
        with pytest.raises(ValidationError):
            _id_selector("a,b")


class TestFastMode:
    def test_disabled_default(self, monkeypatch):
        monkeypatch.delenv("SRP_FAST_MODE", raising=False)
        assert fast_mode_enabled() is False

    def test_enabled_truthy(self, monkeypatch):
        monkeypatch.setenv("SRP_FAST_MODE", "yes")
        assert fast_mode_enabled() is True

    def test_constants(self):
        assert FAST_MODE_TOP_N == 3
        assert FAST_MODE_MAX_PROVIDERS == 1


class TestEmit:
    def test_json(self, capsys):
        emit({"a": 1}, "json")
        out = capsys.readouterr().out
        assert '"a"' in out

    def test_markdown(self, capsys):
        emit("hi", "markdown")
        out = capsys.readouterr().out
        assert out.startswith("```")

    def test_text_topics_empty(self, capsys):
        emit({"topics": []}, "text")
        assert "(no topics)" in capsys.readouterr().out

    def test_text_topics_list(self, capsys):
        emit({"topics": ["a", "b"]}, "text")
        out = capsys.readouterr().out
        assert "a" in out and "b" in out

    def test_text_purposes_empty(self, capsys):
        emit({"purposes": {}}, "text")
        assert "(no purposes)" in capsys.readouterr().out

    def test_text_purposes_dict(self, capsys):
        emit({"purposes": {"x": {"method": "m"}}}, "text")
        assert "x: m" in capsys.readouterr().out

    def test_text_string(self, capsys):
        emit("hello", "text")
        assert "hello" in capsys.readouterr().out

    def test_text_other(self, capsys):
        emit([1, 2], "text")
        assert "1" in capsys.readouterr().out
