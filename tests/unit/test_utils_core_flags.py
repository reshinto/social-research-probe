"""Tests for utils.core.flags."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from social_research_probe.utils.core.flags import service_flag, stage_flag


def test_stage_flag_returns_config_value_when_loaded():
    cfg = MagicMock()
    cfg.stage_enabled.return_value = True
    with patch("social_research_probe.config.load_active_config", return_value=cfg):
        assert stage_flag("fetch", platform="youtube", default=False) is True
    cfg.stage_enabled.assert_called_once_with("youtube", "fetch")


def test_stage_flag_returns_default_on_exception():
    with patch("social_research_probe.config.load_active_config", side_effect=RuntimeError):
        assert stage_flag("fetch", platform="youtube", default=True) is True
        assert stage_flag("fetch", platform="youtube", default=False) is False


def test_service_flag_returns_config_value_when_loaded():
    cfg = MagicMock()
    cfg.service_enabled.return_value = False
    with patch("social_research_probe.config.load_active_config", return_value=cfg):
        assert service_flag("scoring", default=True) is False
    cfg.service_enabled.assert_called_once_with("scoring")


def test_service_flag_returns_default_on_exception():
    with patch("social_research_probe.config.load_active_config", side_effect=RuntimeError):
        assert service_flag("scoring", default=True) is True
        assert service_flag("scoring", default=False) is False
