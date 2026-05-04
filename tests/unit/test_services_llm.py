"""Tests for services.llm package."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import MagicMock, patch

import pytest

from social_research_probe.services.llm.core.output import emit_report
from social_research_probe.technologies.llms import LLMRunner, ensemble, registry
from social_research_probe.utils.core.errors import ValidationError


class _FakeRunner(LLMRunner):
    name = "fake"

    def __init__(self, healthy=True, payload=None, raise_on_run=False):
        self._healthy = healthy
        self._payload = payload or {"ok": True}
        self._raise = raise_on_run

    def health_check(self):
        return self._healthy

    def run(self, prompt, *, schema=None):
        if self._raise:
            raise RuntimeError("nope")
        return self._payload


def test_services_llm_lazy_public_exports():
    import social_research_probe.services.llm as llm_pkg
    import social_research_probe.utils.llm.registry as util_registry
    from social_research_probe.services.llm.core import LLMService, LLMTech
    from social_research_probe.services.llm.core.classify_query import classify_query
    from social_research_probe.services.llm.core.output import emit_report as core_emit_report

    assert llm_pkg.LLMService is LLMService
    assert llm_pkg.LLMTech is LLMTech
    assert llm_pkg.classify_query is classify_query
    assert llm_pkg.emit_report is core_emit_report
    assert llm_pkg.registry is util_registry
    with pytest.raises(AttributeError):
        llm_pkg.__getattr__("missing_export")


class TestRegistry:
    def test_register_requires_name(self):
        class Bad(LLMRunner):
            name = ""

            def health_check(self):
                return True

            def run(self, p, *, schema=None):
                return {}

        with pytest.raises(ValueError):
            registry.register(Bad)

    def test_register_and_get(self, monkeypatch):
        class A(LLMRunner):
            name = "test_register_and_get_a"

            def health_check(self):
                return True

            def run(self, p, *, schema=None):
                return {"ok": True}

        cfg = MagicMock()
        cfg.technology_enabled.return_value = True
        monkeypatch.setattr("social_research_probe.config.load_active_config", lambda *a, **k: cfg)
        registry.register(A)
        assert isinstance(registry.get_runner("test_register_and_get_a"), A)

    def test_get_unknown(self):
        with pytest.raises(ValidationError):
            registry.get_runner("definitely-missing-runner-xyz")

    def test_list_runners_sorted(self):
        names = registry.list_runners()
        assert names == sorted(names)

    def test_run_with_fallback_uses_preferred(self, monkeypatch):
        a = _FakeRunner(healthy=True, payload={"r": "a"})
        b = _FakeRunner(healthy=True, payload={"r": "b"})

        monkeypatch.setattr(registry, "list_runners", lambda: ["a", "b"])
        monkeypatch.setattr(registry, "get_runner", lambda n: a if n == "a" else b)

        out = registry.run_with_fallback("p", schema={}, preferred="a")
        assert out == {"r": "a"}

    def test_run_with_fallback_skips_unhealthy(self, monkeypatch):
        a = _FakeRunner(healthy=False)
        b = _FakeRunner(healthy=True, payload={"r": "b"})
        monkeypatch.setattr(registry, "list_runners", lambda: ["a", "b"])
        monkeypatch.setattr(registry, "get_runner", lambda n: a if n == "a" else b)
        out = registry.run_with_fallback("p", schema={}, preferred="a")
        assert out == {"r": "b"}

    def test_run_with_fallback_skips_failures(self, monkeypatch):
        a = _FakeRunner(raise_on_run=True)
        b = _FakeRunner(payload={"r": "b"})
        monkeypatch.setattr(registry, "list_runners", lambda: ["a", "b"])
        monkeypatch.setattr(registry, "get_runner", lambda n: a if n == "a" else b)
        out = registry.run_with_fallback("p", schema={}, preferred="a")
        assert out == {"r": "b"}

    def test_run_with_fallback_all_fail(self, monkeypatch):
        a = _FakeRunner(healthy=False)
        b = _FakeRunner(raise_on_run=True)
        monkeypatch.setattr(registry, "list_runners", lambda: ["a", "b"])
        monkeypatch.setattr(registry, "get_runner", lambda n: a if n == "a" else b)
        with pytest.raises(ValidationError):
            registry.run_with_fallback("p", schema={}, preferred="a")

    def test_run_with_fallback_preferred_disabled(self, monkeypatch):
        """Preferred runner not in enabled candidates falls back to enabled list."""
        b = _FakeRunner(healthy=True, payload={"r": "b"})
        monkeypatch.setattr(registry, "list_runners", lambda: ["b"])
        monkeypatch.setattr(registry, "get_runner", lambda n: b)
        out = registry.run_with_fallback("p", schema={}, preferred="a")
        assert out == {"r": "b"}

    def test_ensure_runners_registered_runs(self):
        registry.ensure_runners_registered()


class TestRunners:
    def test_prioritize_runner(self):
        assert registry.prioritize_runner(["a", "b", "c"], "b") == ["b", "a", "c"]

    def test_prioritize_runner_already_first(self):
        assert registry.prioritize_runner(["a", "b"], "a") == ["a", "b"]


class TestHost:
    def test_emit_report_writes_envelope(self, capsys):
        emit_report({"x": 1}, "synthesis")
        out = capsys.readouterr().out.strip()
        assert json.loads(out) == {"kind": "synthesis", "report": {"x": 1}}


class TestEnsemble:
    def test_llm_enabled_callable(self, monkeypatch):
        cfg = MagicMock()
        cfg.service_enabled.return_value = True
        monkeypatch.setattr(ensemble, "load_active_config", lambda *a, **k: cfg)
        assert ensemble._llm_enabled() is True

    def test_llm_enabled_no_method(self, monkeypatch):
        class Cfg:
            pass

        monkeypatch.setattr(ensemble, "load_active_config", lambda *a, **k: Cfg())
        assert ensemble._llm_enabled() is True

    def test_service_enabled_disabled(self, monkeypatch):
        cfg = MagicMock()
        cfg.service_enabled.return_value = False
        monkeypatch.setattr(ensemble, "load_active_config", lambda *a, **k: cfg)
        assert ensemble._service_enabled("claude") is False

    def test_collect_responses_empty(self):
        out = asyncio.run(ensemble._collect_responses("p", providers=()))
        assert out == {}

    def test_build_synthesis_prompt_basic(self):
        prompt = ensemble._build_synthesis_prompt("orig", {"a": "x", "b": "y"})
        assert "Response 1" in prompt and "x" in prompt

    def test_synthesize_empty_returns_none(self):
        out = asyncio.run(ensemble._synthesize({}, "p"))
        assert out is None

    def test_synthesize_single_returns_directly(self):
        out = asyncio.run(ensemble._synthesize({"claude": "hello"}, "p"))
        assert out == "hello"

    def test_run_provider_unknown(self):
        out = asyncio.run(ensemble._run_provider("bogus", "p"))
        assert out is None

    def test_run_provider_local_no_bin(self, monkeypatch):
        monkeypatch.delenv("SRP_LOCAL_LLM_BIN", raising=False)
        out = asyncio.run(ensemble._run_provider("local", "p"))
        assert out is None

    def test_multi_llm_prompt_runner_none(self, monkeypatch):
        cfg = MagicMock()
        cfg.service_enabled.return_value = True
        cfg.llm_runner = "none"
        with patch.object(ensemble, "load_active_config", return_value=cfg):
            assert asyncio.run(ensemble.multi_llm_prompt("p")) is None

    def test_multi_llm_prompt_disabled(self, monkeypatch):
        cfg = MagicMock()
        cfg.service_enabled.return_value = False
        with patch.object(ensemble, "load_active_config", return_value=cfg):
            assert asyncio.run(ensemble.multi_llm_prompt("p")) is None


class TestLLMTech:
    from social_research_probe.services.llm.core import LLMTech

    def test_name_property(self):
        from social_research_probe.services.llm.core import LLMTech

        tech = LLMTech("claude", schema={"type": "object"})
        assert tech.name == "llm.claude"

    def test_execute_healthy_runner(self, monkeypatch):
        import asyncio

        from social_research_probe.services.llm.core import LLMTech

        runner = _FakeRunner(healthy=True, payload={"ok": True})
        monkeypatch.setattr(
            "social_research_probe.technologies.llms.registry.get_runner",
            lambda name: runner,
        )
        tech = LLMTech("claude", schema={})
        result = asyncio.run(tech._execute("prompt"))
        assert result == {"ok": True}

    def test_execute_unhealthy_runner_returns_none(self, monkeypatch):
        import asyncio

        from social_research_probe.services.llm.core import LLMTech

        runner = _FakeRunner(healthy=False)
        monkeypatch.setattr(
            "social_research_probe.technologies.llms.registry.get_runner",
            lambda name: runner,
        )
        tech = LLMTech("claude", schema={})
        result = asyncio.run(tech._execute("prompt"))
        assert result is None


class TestLLMService:
    def test_get_technologies_preferred_first(self, monkeypatch):
        from social_research_probe.services.llm.core import LLMService, LLMTech

        monkeypatch.setattr(
            "social_research_probe.technologies.llms.registry.list_runners",
            lambda: ["claude", "gemini"],
        )
        svc = LLMService(preferred="gemini", schema={})
        techs = svc._get_technologies()
        assert [t._runner_name for t in techs] == ["gemini", "claude"]
        assert all(isinstance(t, LLMTech) for t in techs)

    @pytest.mark.asyncio
    async def test_execute_service_fallback(self, monkeypatch):
        from social_research_probe.services import ServiceResult
        from social_research_probe.services.llm.core import LLMService

        svc = LLMService(preferred="claude", schema={})

        class DummyTech:
            def __init__(self, name, result, should_raise=False):
                self.name = name
                self.result = result
                self.should_raise = should_raise
                self.caller_service = ""

            async def execute(self, url):
                if self.should_raise:
                    raise RuntimeError("boom")
                return self.result

        tech1 = DummyTech("t1", None, should_raise=True)
        tech2 = DummyTech("t2", {"success": True})
        monkeypatch.setattr(svc, "_get_technologies", lambda: [tech1, tech2])

        result = await svc.execute_service(
            "data", ServiceResult(service_name="llm", input_key="key", tech_results=[])
        )

        assert len(result.tech_results) == 2
        assert not result.tech_results[0].success
        assert result.tech_results[0].error == "boom"
        assert result.tech_results[1].success
        assert result.tech_results[1].output == {"success": True}

    @pytest.mark.asyncio
    async def test_execute_service_fallback_exhausts_all_failing(self, monkeypatch):
        from social_research_probe.services import ServiceResult
        from social_research_probe.services.llm.core import LLMService

        svc = LLMService(preferred="claude", schema={})

        class DummyTech:
            def __init__(self, name):
                self.name = name
                self.caller_service = ""

            async def execute(self, url):
                return None

        monkeypatch.setattr(svc, "_get_technologies", lambda: [DummyTech("t1"), DummyTech("t2")])
        result = await svc.execute_service(
            "data", ServiceResult(service_name="llm", input_key="key", tech_results=[])
        )
        assert len(result.tech_results) == 2
        assert not result.tech_results[0].success
        assert not result.tech_results[1].success

    @pytest.mark.asyncio
    async def test_execute_service_fallback_no_technologies(self, monkeypatch):
        from social_research_probe.services import ServiceResult
        from social_research_probe.services.llm.core import LLMService

        svc = LLMService(preferred="claude", schema={})
        monkeypatch.setattr(svc, "_get_technologies", lambda: [])
        result = await svc.execute_service(
            "data", ServiceResult(service_name="llm", input_key="key", tech_results=[])
        )
        assert len(result.tech_results) == 0

    @pytest.mark.asyncio
    async def test_execute_service_fallback_success_not_dict(self, monkeypatch):
        from social_research_probe.services import ServiceResult
        from social_research_probe.services.llm.core import LLMService

        svc = LLMService(preferred="claude", schema={})

        class DummyTech:
            def __init__(self, name):
                self.name = name
                self.caller_service = ""

            async def execute(self, url):
                return "string output"

        monkeypatch.setattr(svc, "_get_technologies", lambda: [DummyTech("t1")])
        result = await svc.execute_service(
            "data", ServiceResult(service_name="llm", input_key="key", tech_results=[])
        )
        assert len(result.tech_results) == 1
        assert result.tech_results[0].success

    @pytest.mark.asyncio
    async def test_execute_service_skips_loop_when_pre_populated(self):
        from social_research_probe.services import ServiceResult, TechResult
        from social_research_probe.services.llm.core import LLMService

        svc = LLMService(preferred="claude", schema={})
        pre_tr = TechResult(tech_name="pre", input="data", output={"ok": True}, success=True)
        result = await svc.execute_service(
            "data",
            ServiceResult(service_name="llm", input_key="key", tech_results=[pre_tr]),
        )
        assert len(result.tech_results) == 1
        assert result.tech_results[0].tech_name == "pre"
