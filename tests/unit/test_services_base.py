"""Tests for services.base."""

from __future__ import annotations

import asyncio

import pytest

from social_research_probe.services import BaseService, ServiceResult, TechResult


class _OkTech(BaseTechnology[str, str]):
    name = "ok"

    async def execute(self, data):
        return f"out({data})"

    async def _execute(self, data):
        return f"out({data})"


class _NoneTech(BaseTechnology[str, str]):
    name = "none"

    async def execute(self, data):
        return None

    async def _execute(self, data):
        return None


class _RaiseTech(BaseTechnology[str, str]):
    name = "raise"

    async def execute(self, data):
        raise RuntimeError("boom")

    async def _execute(self, data):
        raise RuntimeError("boom")


class _Service(BaseService[str, str]):
    service_name = "tester"

    def __init__(self, techs):
        self._techs = techs

    def _get_technologies(self):
        return self._techs


def test_tech_result_defaults():
    r = TechResult(tech_name="x", input="i", output="o", success=True)
    assert r.error is None


def test_service_result_defaults():
    r = ServiceResult(service_name="x", input_key="k")
    assert r.tech_results == []


def test_execute_one_success():
    svc = _Service([_OkTech()])
    out = asyncio.run(svc.execute_one("foo"))
    assert out.service_name == "tester"
    assert out.tech_results[0].success is True
    assert out.tech_results[0].output == "out(foo)"


def test_execute_one_none_marks_failure():
    svc = _Service([_NoneTech()])
    out = asyncio.run(svc.execute_one("foo"))
    assert out.tech_results[0].success is False


def test_execute_one_exception_isolated():
    svc = _Service([_RaiseTech(), _OkTech()])
    out = asyncio.run(svc.execute_one("x"))
    fails = [r for r in out.tech_results if r.tech_name == "raise"]
    oks = [r for r in out.tech_results if r.tech_name == "ok"]
    assert fails[0].success is False
    assert "boom" in fails[0].error
    assert oks[0].success is True


def test_execute_batch():
    svc = _Service([_OkTech()])
    out = asyncio.run(svc.execute_batch(["a", "b"]))
    assert len(out) == 2
    assert out[0].tech_results[0].output == "out(a)"


def test_base_service_abstract():
    with pytest.raises(TypeError):
        BaseService()  # type: ignore[abstract]
