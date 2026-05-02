"""Tests for PersistenceService."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

from social_research_probe.services import ServiceResult
from social_research_probe.services.persistence import PersistenceService
from social_research_probe.technologies.persistence.sqlite import SQLitePersistTech


def _run(coro):
    return asyncio.run(coro)


def _dummy_result():
    return ServiceResult(service_name="persistence", input_key="persist", tech_results=[])


def test_service_name():
    assert PersistenceService.service_name == "persistence"


def test_enabled_config_key():
    assert PersistenceService.enabled_config_key == "services.persistence.sqlite"


def test_get_technologies_returns_sqlite_persist_tech():
    techs = PersistenceService()._get_technologies()
    assert len(techs) == 1
    assert isinstance(techs[0], SQLitePersistTech)


def test_execute_service_success():
    fake_output = {
        "db_path": "/tmp/srp.db",
        "run_pk": 1,
        "run_id": "abc123",
        "persisted_source_count": 3,
        "persisted_comment_count": 7,
    }
    svc = PersistenceService()
    with patch.object(SQLitePersistTech, "_execute", new=AsyncMock(return_value=fake_output)):
        result = _run(svc.execute_service({"report": {}}, _dummy_result()))

    assert result.service_name == "persistence"
    assert len(result.tech_results) == 1
    tr = result.tech_results[0]
    assert tr.tech_name == SQLitePersistTech.name
    assert tr.success is True
    assert tr.output == fake_output


def test_execute_service_tech_failure_is_non_fatal():
    svc = PersistenceService()
    with patch.object(
        SQLitePersistTech, "_execute", new=AsyncMock(side_effect=Exception("db error"))
    ):
        result = _run(svc.execute_service({"report": {}}, _dummy_result()))

    assert result.service_name == "persistence"
    assert len(result.tech_results) == 1
    tr = result.tech_results[0]
    assert tr.success is False
    assert tr.output is None
