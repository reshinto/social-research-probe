"""Tests for utils.display.service_log."""

from __future__ import annotations

import asyncio

import pytest

from social_research_probe.utils.display.service_log import (
    logs_enabled,
    service_log,
    service_log_sync,
)


def test_logs_enabled_env(monkeypatch):
    monkeypatch.setenv("SRP_LOGS", "1")
    assert logs_enabled() is True


def test_logs_enabled_cfg(monkeypatch):
    monkeypatch.delenv("SRP_LOGS", raising=False)
    assert logs_enabled(True) is True
    assert logs_enabled(False) is False


def test_service_log_sync_records_ok():
    report: dict = {}
    with service_log_sync("stage", report=report):
        pass
    assert report["stage_timings"][0]["status"] == "ok"
    assert report["stage_timings"][0]["stage"] == "stage"


def test_service_log_sync_records_error():
    report: dict = {}
    with pytest.raises(RuntimeError), service_log_sync("stage", report=report):
        raise RuntimeError("boom")
    timing = report["stage_timings"][0]
    assert timing["status"] == "error"
    assert "boom" in timing["error"]


def test_service_log_sync_emits_when_enabled(capsys, monkeypatch):
    monkeypatch.setenv("SRP_LOGS", "1")
    with service_log_sync("stage", report={}):
        pass
    err = capsys.readouterr().err
    assert "▶" in err and "✓" in err


def test_service_log_sync_emit_failure(capsys, monkeypatch):
    monkeypatch.setenv("SRP_LOGS", "1")
    with pytest.raises(ValueError), service_log_sync("stage", report={}):
        raise ValueError("x")
    assert "✗" in capsys.readouterr().err


def test_service_log_async_ok():
    report: dict = {}

    async def run():
        async with service_log("stage", report=report):
            pass

    asyncio.run(run())
    assert report["stage_timings"][0]["status"] == "ok"


def test_service_log_async_error():
    report: dict = {}

    async def run():
        async with service_log("stage", report=report):
            raise RuntimeError("bad")

    with pytest.raises(RuntimeError):
        asyncio.run(run())
    assert report["stage_timings"][0]["status"] == "error"


def test_service_log_async_emits(capsys, monkeypatch):
    monkeypatch.setenv("SRP_LOGS", "1")

    async def run():
        async with service_log("stage", report={}):
            pass

    asyncio.run(run())
    assert "▶" in capsys.readouterr().err


def test_service_log_async_emit_failure(capsys, monkeypatch):
    monkeypatch.setenv("SRP_LOGS", "1")

    async def run():
        async with service_log("stage", report={}):
            raise RuntimeError("x")

    with pytest.raises(RuntimeError):
        asyncio.run(run())
    assert "✗" in capsys.readouterr().err
