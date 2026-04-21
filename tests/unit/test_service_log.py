"""Tests for the @service_log async context manager and logs_enabled gate."""

from __future__ import annotations

import asyncio

import pytest

from social_research_probe.utils import service_log as sl


def test_logs_enabled_off_by_default(monkeypatch):
    monkeypatch.delenv("SRP_LOGS", raising=False)
    assert sl.logs_enabled(False) is False


def test_logs_enabled_on_via_env(monkeypatch):
    monkeypatch.setenv("SRP_LOGS", "1")
    assert sl.logs_enabled(False) is True


def test_logs_enabled_on_via_cfg(monkeypatch):
    monkeypatch.delenv("SRP_LOGS", raising=False)
    assert sl.logs_enabled(True) is True


def test_logs_enabled_truthy_strings(monkeypatch):
    for value in ("true", "TRUE", "yes", "on"):
        monkeypatch.setenv("SRP_LOGS", value)
        assert sl.logs_enabled(False) is True
    monkeypatch.setenv("SRP_LOGS", "0")
    assert sl.logs_enabled(False) is False


@pytest.mark.asyncio
async def test_service_log_records_ok_timing():
    packet: dict = {}
    async with sl.service_log("demo", packet=packet, cfg_logs_enabled=False):
        await asyncio.sleep(0)
    assert "stage_timings" in packet
    [entry] = packet["stage_timings"]
    assert entry["stage"] == "demo"
    assert entry["status"] == "ok"
    assert entry["error"] == ""
    assert entry["elapsed_s"] >= 0.0


@pytest.mark.asyncio
async def test_service_log_records_error_and_reraises():
    packet: dict = {}
    with pytest.raises(ValueError):
        async with sl.service_log("demo", packet=packet, cfg_logs_enabled=False):
            raise ValueError("boom")
    [entry] = packet["stage_timings"]
    assert entry["status"] == "error"
    assert entry["error"] == "boom"


@pytest.mark.asyncio
async def test_service_log_emits_only_when_enabled(capsys, monkeypatch):
    monkeypatch.delenv("SRP_LOGS", raising=False)
    packet: dict = {}
    async with sl.service_log("quiet", packet=packet, cfg_logs_enabled=False):
        pass
    captured = capsys.readouterr()
    assert captured.err == ""

    async with sl.service_log("loud", packet=packet, cfg_logs_enabled=True):
        pass
    captured = capsys.readouterr()
    assert "loud started" in captured.err
    assert "loud done" in captured.err


@pytest.mark.asyncio
async def test_service_log_nested_stages_both_recorded():
    packet: dict = {}
    async with (
        sl.service_log("outer", packet=packet, cfg_logs_enabled=False),
        sl.service_log("inner", packet=packet, cfg_logs_enabled=False),
    ):
        pass
    stages = [e["stage"] for e in packet["stage_timings"]]
    assert stages == ["inner", "outer"]


@pytest.mark.asyncio
async def test_service_log_emits_failure_line_when_enabled(capsys, monkeypatch):
    monkeypatch.delenv("SRP_LOGS", raising=False)
    packet: dict = {}
    with pytest.raises(RuntimeError):
        async with sl.service_log("oops", packet=packet, cfg_logs_enabled=True):
            raise RuntimeError("kaboom")
    captured = capsys.readouterr()
    assert "oops failed" in captured.err
    assert "kaboom" in captured.err
