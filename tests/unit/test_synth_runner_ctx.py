"""Tests for synthesizing.runner, synthesis_context, formatter, classify_query."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from social_research_probe.services.llm import classify_query as cq
from social_research_probe.services.synthesizing.synthesis import runner, synthesis_context
from social_research_probe.utils.core.errors import DuplicateError, ValidationError


class TestStructuredRunnerOrder:
    def test_none(self):
        assert runner.structured_runner_order("none") == []

    def test_preferred_first(self):
        assert runner.structured_runner_order("gemini")[0] == "gemini"
        assert runner.structured_runner_order("gemini")[-1] in {"local", "codex"}


class TestRunRequiredSynthesis:
    def test_stage_disabled(self, monkeypatch):
        monkeypatch.setattr(runner, "stage_flag", lambda *a, **k: False)
        assert runner.run_required_synthesis({}) is None

    def test_service_disabled(self, monkeypatch):
        monkeypatch.setattr(runner, "stage_flag", lambda *a, **k: True)
        monkeypatch.setattr(runner, "service_flag", lambda *a, **k: False)
        assert runner.run_required_synthesis({}) is None

    def test_runner_none(self, monkeypatch):
        monkeypatch.setattr(runner, "stage_flag", lambda *a, **k: True)
        monkeypatch.setattr(runner, "service_flag", lambda *a, **k: True)
        cfg = MagicMock()
        cfg.default_structured_runner = "none"
        with patch("social_research_probe.config.load_active_config", return_value=cfg):
            assert runner.run_required_synthesis({}) is None

    def test_all_runners_disabled_by_config(self, monkeypatch):
        monkeypatch.setattr(runner, "stage_flag", lambda *a, **k: True)
        monkeypatch.setattr(runner, "service_flag", lambda *a, **k: True)
        cfg = MagicMock()
        cfg.default_structured_runner = "claude"
        cfg.technology_enabled.return_value = False
        with patch("social_research_probe.config.load_active_config", return_value=cfg):
            with patch.object(runner, "build_synthesis_prompt", return_value="p"):
                assert runner.run_required_synthesis({}) is None

    def test_runner_unhealthy(self, monkeypatch):
        monkeypatch.setattr(runner, "stage_flag", lambda *a, **k: True)
        monkeypatch.setattr(runner, "service_flag", lambda *a, **k: True)
        cfg = MagicMock()
        cfg.default_structured_runner = "claude"
        cfg.technology_enabled.return_value = True
        rmock = MagicMock()
        rmock.health_check.return_value = False
        with patch("social_research_probe.config.load_active_config", return_value=cfg):
            with patch.object(runner, "build_synthesis_prompt", return_value="p"):
                with patch.object(runner, "get_runner", return_value=rmock):
                    assert runner.run_required_synthesis({}) is None

    def test_runner_invalid_response(self, monkeypatch):
        monkeypatch.setattr(runner, "stage_flag", lambda *a, **k: True)
        monkeypatch.setattr(runner, "service_flag", lambda *a, **k: True)
        cfg = MagicMock()
        cfg.default_structured_runner = "claude"
        cfg.technology_enabled.return_value = True
        rmock = MagicMock()
        rmock.health_check.return_value = True
        rmock.run.return_value = {}
        with patch("social_research_probe.config.load_active_config", return_value=cfg):
            with patch.object(runner, "build_synthesis_prompt", return_value="p"):
                with patch.object(runner, "get_runner", return_value=rmock):
                    assert runner.run_required_synthesis({}) is None

    def test_runner_succeeds(self, monkeypatch):
        monkeypatch.setattr(runner, "stage_flag", lambda *a, **k: True)
        monkeypatch.setattr(runner, "service_flag", lambda *a, **k: True)
        cfg = MagicMock()
        cfg.default_structured_runner = "claude"
        cfg.technology_enabled.return_value = True
        rmock = MagicMock()
        rmock.health_check.return_value = True
        rmock.run.return_value = {
            "compiled_synthesis": "a",
            "opportunity_analysis": "b",
            "report_summary": "c",
        }
        with patch("social_research_probe.config.load_active_config", return_value=cfg):
            with patch.object(runner, "build_synthesis_prompt", return_value="p"):
                with patch.object(runner, "get_runner", return_value=rmock):
                    out = runner.run_required_synthesis({})
        assert out["compiled_synthesis"] == "a"

    def test_runner_random_exception(self, monkeypatch):
        monkeypatch.setattr(runner, "stage_flag", lambda *a, **k: True)
        monkeypatch.setattr(runner, "service_flag", lambda *a, **k: True)
        cfg = MagicMock()
        cfg.default_structured_runner = "claude"
        cfg.technology_enabled.return_value = True
        rmock = MagicMock()
        rmock.health_check.return_value = True
        rmock.run.side_effect = RuntimeError("boom")
        with patch("social_research_probe.config.load_active_config", return_value=cfg):
            with patch.object(runner, "build_synthesis_prompt", return_value="p"):
                with patch.object(runner, "get_runner", return_value=rmock):
                    assert runner.run_required_synthesis({}) is None


def test_attach_synthesis_single(monkeypatch):
    monkeypatch.setattr(runner, "run_required_synthesis", lambda r: {"x": 1})
    report = {}
    runner.attach_synthesis(report)
    assert report["x"] == 1


def test_attach_synthesis_multi(monkeypatch):
    monkeypatch.setattr(runner, "run_required_synthesis", lambda r: {"y": 2})
    report = {"multi": [{}, {}]}
    runner.attach_synthesis(report)
    assert report["multi"][0]["y"] == 2


def test_attach_synthesis_none_skip(monkeypatch):
    monkeypatch.setattr(runner, "run_required_synthesis", lambda r: None)
    report = {}
    runner.attach_synthesis(report)
    assert report == {}


def test_log_synthesis_runner_status_paths(monkeypatch):
    monkeypatch.setattr(runner, "stage_flag", lambda *a, **k: False)
    runner.log_synthesis_runner_status()
    monkeypatch.setattr(runner, "stage_flag", lambda *a, **k: True)
    monkeypatch.setattr(runner, "service_flag", lambda *a, **k: False)
    runner.log_synthesis_runner_status()
    monkeypatch.setattr(runner, "service_flag", lambda *a, **k: True)
    cfg = MagicMock()
    cfg.default_structured_runner = "none"
    with patch("social_research_probe.config.load_active_config", return_value=cfg):
        runner.log_synthesis_runner_status()
    cfg.default_structured_runner = "claude"
    rmock = MagicMock()
    rmock.health_check.return_value = False
    with patch("social_research_probe.config.load_active_config", return_value=cfg):
        with patch.object(runner, "get_runner", return_value=rmock):
            runner.log_synthesis_runner_status()


class TestSynthesisContext:
    def test_empty_report(self):
        ctx = synthesis_context.build_synthesis_context({})
        assert ctx["topic"] == "" and ctx["items"] == []

    def test_full_report(self):
        report = {
            "topic": "ai",
            "platform": "youtube",
            "platform_engagement_summary": "ok",
            "evidence_summary": "great",
            "stats_summary": {"highlights": ["mean: 0.5; n=10"]},
            "chart_takeaways": ["c"],
            "warnings": ["w"],
            "items_top_n": [
                {
                    "title": "T",
                    "url": "u",
                    "scores": {"overall": 0.9},
                    "one_line_takeaway": "tk",
                    "summary": "s",
                    "corroboration_verdict": "supported",
                }
            ],
            "source_validation_summary": {
                "validated": 1,
                "partially": 0,
                "unverified": 0,
                "low_trust": 0,
                "primary": 1,
                "secondary": 0,
                "commentary": 0,
                "notes": "",
            },
        }
        ctx = synthesis_context.build_synthesis_context(report)
        assert ctx["topic"] == "ai"
        assert ctx["items"][0]["rank"] == 1
        assert ctx["items"][0]["scores"]["overall"] == 0.9
        assert ctx["coverage"]["fetched"] == 10

    def test_fetched_from_highlights_no_match(self):
        assert synthesis_context._fetched_from_highlights(["nothing here"]) is None

    def test_fetched_from_highlights_match(self):
        assert synthesis_context._fetched_from_highlights(["mean=5 n=20 other"]) == 20


class TestClassifyQuery:
    def test_validate_service_disabled(self):
        cfg = MagicMock()
        cfg.service_enabled.return_value = False
        with patch(
            "social_research_probe.services.llm.classify_query.load_active_config", return_value=cfg
        ):
            with pytest.raises(ValidationError):
                cq._validate_llm_config()

    def test_validate_runner_none(self):
        cfg = MagicMock()
        cfg.service_enabled.return_value = True
        cfg.default_structured_runner = "none"
        with patch(
            "social_research_probe.services.llm.classify_query.load_active_config", return_value=cfg
        ):
            with pytest.raises(ValidationError):
                cq._validate_llm_config()

    def test_validate_ok(self):
        cfg = MagicMock()
        cfg.service_enabled.return_value = True
        cfg.default_structured_runner = "claude"
        with patch(
            "social_research_probe.services.llm.classify_query.load_active_config", return_value=cfg
        ):
            assert cq._validate_llm_config() == "claude"

    def test_is_valid_result_ok(self):
        assert cq._is_valid_result({"topic": "x", "purpose_name": "y", "purpose_method": "z"})

    def test_is_valid_result_missing(self):
        assert not cq._is_valid_result({"topic": "x"})

    def test_is_valid_result_empty_string(self):
        assert not cq._is_valid_result({"topic": " ", "purpose_name": "y", "purpose_method": "z"})

    def test_persist_topic_new(self, monkeypatch):
        monkeypatch.setattr(cq, "add_topics", lambda v, force: None)
        assert cq._persist_topic("x") is True

    def test_persist_topic_dup(self, monkeypatch):
        def boom(v, force):
            raise DuplicateError("d")

        monkeypatch.setattr(cq, "add_topics", boom)
        assert cq._persist_topic("x") is False

    def test_persist_purpose_new(self, monkeypatch):
        monkeypatch.setattr(cq, "add_purpose", lambda **kw: None)
        assert cq._persist_purpose("n", "m") is True

    def test_persist_purpose_dup(self, monkeypatch):
        def boom(**kw):
            raise DuplicateError("d")

        monkeypatch.setattr(cq, "add_purpose", boom)
        assert cq._persist_purpose("n", "m") is False

    def test_build_prompt(self):
        out = cq._build_classification_prompt("q", [], [])
        assert "(none yet)" in out
        out = cq._build_classification_prompt("q", ["t"], ["p"])
        assert "t" in out and "p" in out

    def test_run_classification_cached(self, monkeypatch):
        monkeypatch.setattr(cq, "get_json", lambda c, k: {"result": {"a": 1}})
        out = cq._run_classification("p", preferred="claude")
        assert out == {"a": 1}

    def test_run_classification_invalid_raises(self, monkeypatch):
        monkeypatch.setattr(cq, "get_json", lambda c, k: None)
        monkeypatch.setattr(cq, "run_with_fallback", lambda p, s, r: {})
        with pytest.raises(ValidationError):
            cq._run_classification("p", preferred="claude")

    def test_run_classification_valid(self, monkeypatch):
        monkeypatch.setattr(cq, "get_json", lambda c, k: None)
        monkeypatch.setattr(cq, "set_json", lambda *a, **k: None)
        monkeypatch.setattr(
            cq,
            "run_with_fallback",
            lambda p, s, r: {"topic": "t", "purpose_name": "n", "purpose_method": "m"},
        )
        out = cq._run_classification("p", preferred="claude")
        assert out["topic"] == "t"

    def test_classify_query_full(self, monkeypatch, tmp_path: Path):
        cfg = MagicMock()
        cfg.data_dir = tmp_path
        cfg.service_enabled.return_value = True
        cfg.default_structured_runner = "claude"
        with patch(
            "social_research_probe.services.llm.classify_query.load_active_config", return_value=cfg
        ):
            with patch("social_research_probe.config.load_active_config", return_value=cfg):
                monkeypatch.setattr(cq, "list_topics", lambda: [])
                monkeypatch.setattr(cq, "load", lambda: {"purposes": {}})
                monkeypatch.setattr(
                    cq,
                    "_run_classification",
                    lambda p, preferred: {
                        "topic": "T",
                        "purpose_name": "P",
                        "purpose_method": "M",
                    },
                )
                monkeypatch.setattr(cq, "add_topics", lambda v, force: None)
                monkeypatch.setattr(cq, "add_purpose", lambda **kw: None)
                out = cq.classify_query("hello")
        assert out.topic == "t"
        assert out.purpose_name == "p"
        assert out.topic_created is True
