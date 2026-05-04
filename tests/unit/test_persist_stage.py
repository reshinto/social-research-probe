"""Tests for YouTubePersistStage."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from social_research_probe.platforms.state import PipelineState
from social_research_probe.platforms.youtube import YouTubePersistStage, YouTubePipeline


def _run(coro):
    return asyncio.run(coro)


def _state(report: dict | None = None) -> PipelineState:
    state = PipelineState(platform_type="youtube", cmd=None, cache=None, platform_config={})
    if report is not None:
        state.outputs["report"] = report
    return state


def _enabled_cfg(db_enabled: bool = True) -> MagicMock:
    cfg = MagicMock()
    cfg.stage_enabled.return_value = True
    cfg.raw = {
        "database": {
            "enabled": db_enabled,
            "persist_transcript_text": False,
            "persist_comment_text": True,
        }
    }
    cfg.database_path = Path("/tmp/srp.db")
    return cfg


def _fake_success_results(output: dict) -> list:
    tr = MagicMock()
    tr.success = True
    tr.output = output
    tr.error = None
    result = MagicMock()
    result.tech_results = [tr]
    return [result]


def _fake_failure_results(error: str = "disk full") -> list:
    tr = MagicMock()
    tr.success = False
    tr.output = None
    tr.error = error
    result = MagicMock()
    result.tech_results = [tr]
    return [result]


# --- stage_name ---


def test_stage_name():
    assert YouTubePersistStage().stage_name == "persist"


# --- no-op conditions ---


def test_no_op_when_report_missing():
    state = _state()
    with patch(
        "social_research_probe.services.persistence.PersistenceService.execute_batch",
        new=AsyncMock(),
    ) as mock_svc:
        _run(YouTubePersistStage().execute(state))
    mock_svc.assert_not_called()


def test_no_op_when_report_empty_dict():
    state = _state(report={})
    with patch(
        "social_research_probe.services.persistence.PersistenceService.execute_batch",
        new=AsyncMock(),
    ) as mock_svc:
        _run(YouTubePersistStage().execute(state))
    mock_svc.assert_not_called()


def test_no_op_when_stage_disabled():
    state = _state(report={"topic": "test"})
    mock_cfg = MagicMock()
    mock_cfg.stage_enabled.return_value = False
    with patch("social_research_probe.config.load_active_config", return_value=mock_cfg):
        with patch(
            "social_research_probe.services.persistence.PersistenceService.execute_batch",
            new=AsyncMock(),
        ) as mock_svc:
            _run(YouTubePersistStage().execute(state))
    mock_svc.assert_not_called()


def test_no_op_when_database_disabled():
    state = _state(report={"topic": "test"})
    with patch(
        "social_research_probe.config.load_active_config",
        return_value=_enabled_cfg(db_enabled=False),
    ):
        with patch(
            "social_research_probe.services.persistence.PersistenceService.execute_batch",
            new=AsyncMock(),
        ) as mock_svc:
            _run(YouTubePersistStage().execute(state))
    mock_svc.assert_not_called()


# --- success path ---


def test_calls_persistence_service_when_enabled():
    fake_output = {"db_path": "/tmp/srp.db", "run_pk": 1, "run_id": "abc123"}
    state = _state(report={"topic": "test"})
    with patch("social_research_probe.config.load_active_config", return_value=_enabled_cfg()):
        with patch(
            "social_research_probe.services.persistence.PersistenceService.execute_batch",
            new=AsyncMock(return_value=_fake_success_results(fake_output)),
        ) as mock_svc:
            result_state = _run(YouTubePersistStage().execute(state))

    mock_svc.assert_called_once()
    stage_out = result_state.outputs["stages"]["persist"]
    assert stage_out["db_path"] == "/tmp/srp.db"
    assert stage_out["run_id"] == "abc123"


def test_success_without_run_id_keeps_stage_output_without_report_run_id():
    fake_output = {"db_path": "/tmp/srp.db", "run_pk": 1}
    state = _state(report={"topic": "test"})
    with patch("social_research_probe.config.load_active_config", return_value=_enabled_cfg()):
        with patch(
            "social_research_probe.services.persistence.PersistenceService.execute_batch",
            new=AsyncMock(return_value=_fake_success_results(fake_output)),
        ):
            result_state = _run(YouTubePersistStage().execute(state))

    stage_out = result_state.outputs["stages"]["persist"]
    assert stage_out["db_path"] == "/tmp/srp.db"
    assert stage_out["run_id"] is None
    assert "run_id" not in result_state.outputs["report"]


# --- failure path ---


def test_appends_warning_on_failure():
    state = _state(report={"topic": "test"})
    with patch("social_research_probe.config.load_active_config", return_value=_enabled_cfg()):
        with patch(
            "social_research_probe.services.persistence.PersistenceService.execute_batch",
            new=AsyncMock(return_value=_fake_failure_results("disk full")),
        ):
            result_state = _run(YouTubePersistStage().execute(state))

    warnings = result_state.outputs["report"].get("warnings", [])
    assert any("persistence" in w for w in warnings)
    assert any("disk full" in w for w in warnings)


def test_success_with_non_dict_output_does_not_set_stage_output():
    tr = MagicMock()
    tr.success = True
    tr.output = "not-a-dict"
    result = MagicMock()
    result.tech_results = [tr]
    state = _state(report={"topic": "test"})
    with patch("social_research_probe.config.load_active_config", return_value=_enabled_cfg()):
        with patch(
            "social_research_probe.services.persistence.PersistenceService.execute_batch",
            new=AsyncMock(return_value=[result]),
        ):
            result_state = _run(YouTubePersistStage().execute(state))

    assert "persist" not in result_state.outputs.get("stages", {})


def test_appends_generic_warning_when_no_error_message():
    state = _state(report={"topic": "test"})
    with patch("social_research_probe.config.load_active_config", return_value=_enabled_cfg()):
        with patch(
            "social_research_probe.services.persistence.PersistenceService.execute_batch",
            new=AsyncMock(return_value=_fake_failure_results("")),
        ):
            result_state = _run(YouTubePersistStage().execute(state))

    warnings = result_state.outputs["report"].get("warnings", [])
    assert any("sqlite persist failed" in w for w in warnings)


# --- pipeline order ---


def test_persist_stage_runs_after_export_in_pipeline_order():
    groups = YouTubePipeline().stages()
    export_idx = next(i for i, g in enumerate(groups) if any(s.stage_name == "export" for s in g))
    persist_idx = next(i for i, g in enumerate(groups) if any(s.stage_name == "persist" for s in g))
    assert persist_idx > export_idx


def test_persist_stage_is_last_group():
    groups = YouTubePipeline().stages()
    last_group = groups[-1]
    assert any(s.stage_name == "persist" for s in last_group)
