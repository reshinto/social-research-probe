"""Tests for utils.display.progress."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from unittest.mock import patch

import pytest

from social_research_probe.utils.display import progress


@pytest.fixture
def logs_on(monkeypatch):
    monkeypatch.setenv("SRP_LOGS", "1")


@pytest.fixture
def logs_off(monkeypatch):
    monkeypatch.delenv("SRP_LOGS", raising=False)


def test_log_silent_when_disabled(logs_off, capsys):
    with patch("social_research_probe.config.load_active_config", side_effect=RuntimeError):
        progress.log("hello")
    assert capsys.readouterr().err == ""


def test_log_writes_when_enabled(logs_on, capsys):
    progress.log("hello")
    assert "hello" in capsys.readouterr().err


def test_timed_operation_success(logs_on, capsys):
    with progress.timed_operation("op"):
        pass
    assert "outcome=success" in capsys.readouterr().err


def test_timed_operation_error_reraises(logs_on, capsys):
    with pytest.raises(ValueError), progress.timed_operation("op"):
        raise ValueError("boom")
    out = capsys.readouterr().err
    assert "outcome=error" in out


def test_compact_value_short():
    assert progress._compact_value("ab", max_chars=10) == "'ab'"


def test_compact_value_truncated():
    s = progress._compact_value("x" * 100, max_chars=10)
    assert s.endswith("...")
    assert len(s) == 10


def test_compact_value_dict_summary():
    s = progress._compact_value({"k": 1}, max_chars=200)
    assert "k" in s


def test_compact_value_sequence():
    s = progress._compact_value([1, 2, 3, 4], max_chars=200)
    assert "len" in s


@dataclass
class _Sample:
    a: int
    b: str


def test_compact_value_dataclass():
    s = progress._compact_value(_Sample(a=1, b="x"), max_chars=200)
    assert "_Sample" in s


def test_log_with_time_sync(logs_on, capsys):
    @progress.log_with_time("doing {x}")
    def f(x):
        return x * 2

    assert f(3) == 6
    err = capsys.readouterr().err
    assert "doing 3 input=" in err
    assert "outcome=success" in err


def test_log_with_time_sync_error(logs_on, capsys):
    @progress.log_with_time("op")
    def f():
        raise RuntimeError("bad")

    with pytest.raises(RuntimeError):
        f()
    assert "outcome=error" in capsys.readouterr().err


def test_log_with_time_async(logs_on, capsys):
    @progress.log_with_time("async op")
    async def f(x):
        return x + 1

    assert asyncio.run(f(2)) == 3
    assert "outcome=success" in capsys.readouterr().err


def test_log_with_time_async_error(logs_on, capsys):
    @progress.log_with_time("async op")
    async def f():
        raise RuntimeError("nope")

    with pytest.raises(RuntimeError):
        asyncio.run(f())
    assert "outcome=error" in capsys.readouterr().err
