"""Tests for social_research_probe.cli.dsl."""

from __future__ import annotations

import pytest

from social_research_probe.cli.dsl import (
    _take_quoted,
    parse_name_method,
    parse_quoted_list,
    parse_topic_values,
)
from social_research_probe.utils.core.errors import ValidationError


def test_take_quoted_ok():
    assert _take_quoted('"abc"', 0) == ("abc", 5)


def test_take_quoted_missing_open_quote():
    with pytest.raises(ValidationError, match="expected"):
        _take_quoted("abc", 0)


def test_take_quoted_unterminated():
    with pytest.raises(ValidationError, match="unterminated"):
        _take_quoted('"abc', 0)


def test_take_quoted_pos_past_end():
    with pytest.raises(ValidationError):
        _take_quoted('"x"', 5)


def test_parse_quoted_list_single():
    assert parse_quoted_list('"a"') == ["a"]


def test_parse_quoted_list_multi():
    assert parse_quoted_list('"a"|"b"|"c"') == ["a", "b", "c"]


def test_parse_quoted_list_bad_separator():
    with pytest.raises(ValidationError, match="expected '\\|'"):
        parse_quoted_list('"a"X"b"')


def test_parse_topic_values_dsl():
    assert parse_topic_values(['"a"|"b"']) == ["a", "b"]


def test_parse_topic_values_passthrough():
    assert parse_topic_values(["a", "b"]) == ["a", "b"]


def test_parse_name_method_dsl():
    assert parse_name_method(['"trends"="track"']) == ("trends", "track")


def test_parse_name_method_positional():
    assert parse_name_method(["trends", "track"]) == ("trends", "track")


def test_parse_name_method_bad_separator():
    with pytest.raises(ValidationError, match="expected"):
        parse_name_method(['"trends"-"track"'])


def test_parse_name_method_trailing_content():
    with pytest.raises(ValidationError, match="trailing"):
        parse_name_method(['"trends"="track"extra'])


def test_parse_name_method_wrong_arity():
    with pytest.raises(ValidationError, match="--add"):
        parse_name_method(["only-one"])
