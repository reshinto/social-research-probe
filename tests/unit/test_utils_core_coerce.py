"""Tests for utils.core.coerce."""

from __future__ import annotations

from social_research_probe.utils.core.coerce import (
    as_optional_string,
    coerce_int,
    coerce_object,
    coerce_string,
    parse_duration_seconds,
)


class TestCoerceObject:
    def test_dict_returned_as_is(self):
        assert coerce_object({"a": 1}) == {"a": 1}

    def test_non_dict_returns_empty(self):
        assert coerce_object(None) == {}
        assert coerce_object("x") == {}
        assert coerce_object([1, 2]) == {}


class TestCoerceString:
    def test_string_returned(self):
        assert coerce_string("hello") == "hello"

    def test_non_string_returns_empty(self):
        assert coerce_string(42) == ""
        assert coerce_string(None) == ""


class TestAsOptionalString:
    def test_non_empty_string(self):
        assert as_optional_string("x") == "x"

    def test_empty_string_returns_none(self):
        assert as_optional_string("") is None

    def test_non_string_returns_none(self):
        assert as_optional_string(0) is None
        assert as_optional_string(None) is None


class TestCoerceInt:
    def test_bool(self):
        assert coerce_int(True) == 1
        assert coerce_int(False) == 0

    def test_int(self):
        assert coerce_int(7) == 7

    def test_float(self):
        assert coerce_int(3.7) == 3

    def test_numeric_string(self):
        assert coerce_int("42") == 42

    def test_invalid_string(self):
        assert coerce_int("abc") == 0

    def test_other_types(self):
        assert coerce_int(None) == 0
        assert coerce_int([1]) == 0


class TestParseDurationSeconds:
    def test_full(self):
        assert parse_duration_seconds("PT1H2M3S") == 3723

    def test_minutes_only(self):
        assert parse_duration_seconds("PT5M") == 300

    def test_seconds_only(self):
        assert parse_duration_seconds("PT45S") == 45

    def test_hours_only(self):
        assert parse_duration_seconds("PT2H") == 7200

    def test_invalid_returns_zero(self):
        assert parse_duration_seconds("garbage") == 0

    def test_empty_pt_returns_zero(self):
        assert parse_duration_seconds("PT") == 0
