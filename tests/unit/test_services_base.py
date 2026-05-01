"""Tests for services.base."""

from __future__ import annotations

import asyncio

import pytest

from social_research_probe.services import BaseService, ServiceResult, TechResult
from social_research_probe.technologies import BaseTechnology


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

    async def execute_service(self, data, result):
        return result


class _NoTechService(BaseService[str, str]):
    service_name = "no_tech"

    def _get_technologies(self):
        return [None]

    async def execute_service(self, data, result):
        result.tech_results.append(
            TechResult(
                tech_name="local_logic",
                input=data,
                output=f"local({data})",
                success=True,
            )
        )
        return result


class _EmptyTechService(BaseService[str, str]):
    service_name = "empty_tech"

    def _get_technologies(self):
        return []

    async def execute_service(self, data, result):
        return result


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


def test_execute_one_supports_no_technology_sentinel():
    svc = _NoTechService()
    out = asyncio.run(svc.execute_one("foo"))
    assert out.tech_results[0].tech_name == "local_logic"
    assert out.tech_results[0].output == "local(foo)"


def test_get_technologies_must_not_return_empty_list():
    svc = _EmptyTechService()
    with pytest.raises(ValueError, match=r"\[None\]"):
        asyncio.run(svc.execute_one("foo"))


def test_base_service_abstract():
    with pytest.raises(TypeError):
        BaseService()  # type: ignore[abstract]


def test_subclasses_cannot_override_protected_lifecycle_methods():
    with pytest.raises(TypeError, match="execute_service"):

        class _BadService(BaseService[str, str]):
            service_name = "bad"

            def _get_technologies(self):
                return []

            async def execute_service(self, data, result):
                return ServiceResult(service_name="bad", input_key="x")

            async def execute_one(self, data):
                return ServiceResult(service_name="bad", input_key="x")


class _CacheableTech(BaseTechnology[str, str]):
    name = "cacheable_tech"

    async def _execute(self, data):
        return {"result": f"computed({data})"}


class _NonCacheableTech(BaseTechnology[str, str]):
    name = "noncacheable_tech"
    cacheable = False

    async def _execute(self, data):
        return {"result": f"computed({data})"}


class _NonSerializableTech(BaseTechnology[str, str]):
    name = "nonserializable_tech"

    async def _execute(self, data):
        return object()


class _NoneResultTech(BaseTechnology[str, str]):
    name = "none_tech"

    async def _execute(self, data):
        return None


class TestTechnologyCachedExecute:
    def test_not_cacheable_skips_cache(self, monkeypatch):
        monkeypatch.delenv("SRP_DISABLE_CACHE", raising=False)
        tech = _NonCacheableTech()
        result = asyncio.run(tech.execute("x"))
        assert result == {"result": "computed(x)"}

    def test_cache_disabled_skips_cache(self, monkeypatch):
        monkeypatch.setenv("SRP_DISABLE_CACHE", "1")
        tech = _CacheableTech()
        result = asyncio.run(tech.execute("x"))
        assert result == {"result": "computed(x)"}

    def test_cache_miss_stores_result(self, monkeypatch, tmp_path):
        monkeypatch.setenv("SRP_DATA_DIR", str(tmp_path))
        monkeypatch.delenv("SRP_DISABLE_CACHE", raising=False)
        tech = _CacheableTech()
        result = asyncio.run(tech.execute("x"))
        assert result == {"result": "computed(x)"}

    def test_cache_hit_returns_cached(self, monkeypatch, tmp_path):
        monkeypatch.setenv("SRP_DATA_DIR", str(tmp_path))
        monkeypatch.delenv("SRP_DISABLE_CACHE", raising=False)
        tech = _CacheableTech()
        asyncio.run(tech.execute("x"))
        result = asyncio.run(tech.execute("x"))
        assert result == {"result": "computed(x)"}

    def test_non_serializable_result_swallowed(self, monkeypatch, tmp_path):
        monkeypatch.setenv("SRP_DATA_DIR", str(tmp_path))
        monkeypatch.delenv("SRP_DISABLE_CACHE", raising=False)
        tech = _NonSerializableTech()
        result = asyncio.run(tech.execute("x"))
        assert result is not None

    def test_none_result_not_cached(self, monkeypatch, tmp_path):
        monkeypatch.setenv("SRP_DATA_DIR", str(tmp_path))
        monkeypatch.delenv("SRP_DISABLE_CACHE", raising=False)
        tech = _NoneResultTech()
        result = asyncio.run(tech.execute("x"))
        assert result is None
